import asyncio
import mutagen
import mutagen.easyid3
import os
import os.path
import shutil
import string
from typing import (
    Dict,
    List,
    Optional,
    Union,
    cast
)
from .albumdata import Albumdata, Track
from .dependency import Dependency
from .config import Config
from .error import CdparacordError


class RipError(CdparacordError):
    pass


class Rip:
    def __init__(
            self,
            albumdata: Albumdata,
            deps: Dependency,
            config: Config,
            begin_track: int,
            end_track: int,
            continue_rip: bool):
        self._albumdata = albumdata
        self._deps = deps
        self._config = config
        self._begin_track = begin_track
        self._end_track = end_track
        # We can only rip one thing at once
        self._rip_lock = asyncio.Lock()
        # TODO TODO TODO this is NOT HANDLED yet
        # It should be checked and based on it we should see which
        # tracks need ripping, which need encoding, which need tagging
        # and schedule *only* those activities (and the ones that come
        # after them automatically)
        self._continue_rip = continue_rip
        # Here's where the temporary -> permanent filenames are recorded
        # so we can move them to the target dir
        self._tagged_files: Dict[str, str] = {}

    def _arg_expand(
            self,
            task_args: List[str],
            one_file: str, 
            *,
            all_files: Optional[List[str]] = None,
            out_file: Optional[str] = None) -> List[str]:
        """Expand placeholders in task arguments.

        If all_files is not None, the all_files placeholder will be
        substituted. Otherwise it won't. Same for out_file.
        """
        final_args: List[str] = []
        placeholder = '<ALLFILES_PLACEHOLDER>'
        for arg in task_args:
            template = string.Template(arg)
            subs = {'one_file': one_file}
            if all_files is not None:
                subs['all_files'] = placeholder
            if out_file is not None:
                subs['out_file'] = out_file

            # If all_files is used just dump files into args
            # It's not an "actual" template thing. Because reasons.
            res = template.substitute(subs)
            if res == placeholder:
                final_args.extend(cast(List[str], all_files))
            else:
                final_args.append(res)
        return final_args

    async def _tag_track(
            self,
            track: Track,
            temp_encoded: str) -> None:
        """Tag track and plop it in the dict."""
        audiofile: Union[mutagen.easyid3.EasyID3, mutagen.FileType]
        try:
            audiofile = mutagen.easyid3.EasyID3(temp_encoded)
        except mutagen.MutagenError:
            audiofile = mutagen.File(temp_encoded, easy=True)
            audiofile.add_tags()

        # We only tag albumartist on multi-artist albums, or if we're
        # set to always tag albumartist.
        if (self._albumdata.multiartist
                or self._config.get('always_tag_albumartist')):
            audiofile['albumartist'] = self._albumdata.albumartist

        # This is information we always save and presumably always have
        audiofile['artist'] = track.artist
        audiofile['album'] = self._albumdata.title
        audiofile['title'] = track.title
        audiofile['tracknumber'] = str(track.tracknumber)
        audiofile['date'] = self._albumdata.date

        audiofile.save()

        print("Tagged {}".format(track.filename))

        self._tagged_files[temp_encoded] = track.filename

    async def _encode_track(
            self,
            track: Track,
            temp_filename: str) -> None:
        """Encode track and kick off tag and post_encode."""
        temp_encoded = os.path.join(
            self._albumdata.ripdir,
            '{tracknumber}{ext}'.format(
                tracknumber=track.tracknumber,
                ext=os.path.splitext(track.filename)[1]))
        encoder = self._config.get('encoder')
        encoder_name = list(encoder.keys())[0]
        encoder_args = self._arg_expand(
            encoder[encoder_name], temp_filename, out_file=temp_encoded)

        proc = await asyncio.create_subprocess_exec(
            self._deps.encoder,
            *encoder_args)

        if await proc.wait() != 0:
            raise RipError('Failed to encode track {}'.format(track.filename))

        # Run post_encode
        for task in self._config.get('post_encode'):
            # Parsing the ansible-y format
            task_name = list(task.keys())[0]
            task_args = self._arg_expand(task[task_name], temp_encoded)
            # Create actual task after preprocessing args
            proc = await asyncio.create_subprocess_exec(
                task_name,
                *task_args)

            if await proc.wait() != 0:
                raise RipError('post_encode task {} failed'.format(
                    task_name))

        # Always run after the previous due to awaits
        await self._tag_track(track, temp_encoded)

    async def _rip_track(self, track: Track) -> None:
        """Rip track and kick off encoder and post_rip."""
        # Create temp filename here before acquiring lock to minimise
        # time locked and because I want to
        temp_filename = os.path.join(
            self._albumdata.ripdir,
            '{tracknumber}.wav'.format(tracknumber=track.tracknumber))
        temp_rip = '{temp_filename}.rip'.format(temp_filename=temp_filename)

        # Acquire lock on, essentially, the CD drive
        async with self._rip_lock:
            proc = await asyncio.create_subprocess_exec(
                self._deps.cdparanoia,
                '--',
                str(track.tracknumber),
                temp_rip)

            if await proc.wait() != 0:
                raise RipError('Ripping track {} failed'.format(
                    track.tracknumber))

        # Rip lock released
        # Run post_rip tasks. No gather, we just await them
        for task in self._config.get('post_rip'):
            # Parsing the ansible-y format
            task_name = list(task.keys())[0]
            task_args = self._arg_expand(task[task_name], temp_rip)
            # Create actual task after preprocessing args
            proc = await asyncio.create_subprocess_exec(
                task_name,
                *task_args)

            if await proc.wait() != 0:
                raise RipError('post_rip task {} failed'.format(
                    task_name))

        # Move the file to the actual temp filename
        # This means the presence of <number>.wav signifies both ripping
        # and post_rip tasks were completed succesfully.
        os.rename(temp_rip, temp_filename)

        # Always run after the previous due to awaits
        await self._encode_track(track, temp_filename)

    async def _post_finished(self) -> None:
        """Run post_finished tasks.

        These are a bit more hefty than the other ones so they get their
        own coro.
        """
        for task in self._config.get('post_finished'):
            # Parsing the ansible-y format
            task_name = list(task.keys())[0]
            per_file = False
            # See if we need to run this task per-file
            # TODO: Need better way to do this
            for arg in task[task_name]:
                if ('${one_file}' in arg
                        or '$one_file' in arg):
                    per_file = True
                    break

            if per_file:
                for one_file in self._tagged_files:
                    task_args = self._arg_expand(
                        task[task_name],
                        one_file,
                        all_files=list(self._tagged_files.keys()))
                    # Create actual task after preprocessing args
                    proc = await asyncio.create_subprocess_exec(
                        task_name,
                        *task_args)

                    if await proc.wait() != 0:
                        raise RipError('post_finished task {} failed'.format(
                            task_name))
            else:
                task_args = self._arg_expand(
                    task[task_name],
                    '/dev/null',
                    all_files=list(self._tagged_files.keys()))
                # Create actual task after preprocessing args
                proc = await asyncio.create_subprocess_exec(
                    task_name,
                    *task_args)

                if await proc.wait() != 0:
                    raise RipError('post_finished task {} failed'.format(
                        task_name))

    def rip_pipeline(self) -> None:
        """Rip cd and run given extra tasks.

        See config.py for more
        """
        loop = asyncio.get_event_loop()
        tasks = []
        # Schedule each track to be ripped
        # If we continue rip we might only schedule them to be encoded.
        for track in self._albumdata.tracks:
            if not (self._begin_track <= track.tracknumber <= self._end_track):
                # Do not rip this track
                continue
            # File that would exist if rip for this track has
            # succesfully completed
            ripped_filename = os.path.join(
                    self._albumdata.ripdir,
                    '{}.wav'.format(track.tracknumber))
            if os.path.isfile(ripped_filename) and self._continue_rip:
                # We have the .wav - this signals that we have
                # succesfully ripped this track and only need to
                # encode it. If we've encoded it in the past, that
                # is of no consequence - it's easier to treat only rip
                # as the time-consuming part (and it's possible encoder
                # settings have changed between rips, etc)
                tasks.append(asyncio.ensure_future(
                        self._encode_track(track, ripped_filename)))
            else:
                # Ripped file didn't exist or we're not continuing,
                # schedule it to be ripped
                tasks.append(asyncio.ensure_future(self._rip_track(track)))

        # Wait for all to finish
        # NOTE: gather order is not in fact specified, so tracks may be
        # ripped in a strange order. I've never observed this, just
        # something to keep in mind.
        loop.run_until_complete(asyncio.gather(*tasks))
        loop.run_until_complete(asyncio.ensure_future(self._post_finished()))

        # We're done with the tasks
        for one_file in self._tagged_files:
            target_file = self._tagged_files[one_file]
            # Ensure target dir exists
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            # Copy files over
            shutil.copy2(one_file, target_file)

        loop.close()
        # Done!
