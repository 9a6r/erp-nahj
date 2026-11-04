"""Validate a trusted Nahj backup before recovery; never execute its Compose file.

Checksums detect damage, not authorship. Only restore backups from a trusted
source: a database dump contains SQL and may contain integration credentials.
This module also runs inside the pinned server image without desktop libraries.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tarfile


class BackupError(ValueError):
    pass


def read_json(path):
    if path.stat().st_size > 1024 * 1024:
        raise BackupError('Backup metadata is too large.')
    try:
        value = json.loads(path.read_text())
    except (ValueError, UnicodeError):
        raise BackupError('Invalid backup metadata.') from None
    if not isinstance(value, dict):
        raise BackupError('Invalid backup metadata.')
    return value


def attachment_path(member, site, visibility):
    parts = PurePosixPath(member.name).parts
    prefix = (site, visibility, 'files')
    if ('..' in parts or '\\' in member.name or parts[:3] != prefix
            or not (member.isdir() or member.isfile())
            or (len(parts) == 3 and not member.isdir())):
        raise BackupError('Unsafe attachment path or file type in backup.')
    return parts[1:]


def inspect_backup(directory, image_id):
    if not str(directory).strip():
        raise BackupError('Select a backup folder containing manifest.json.')
    root = Path(directory).expanduser()
    if not root.is_dir():
        raise BackupError('Select a backup folder containing manifest.json.')
    # Reject links and subdirectories, including the manifest itself.
    for file in root.iterdir():
        if not stat.S_ISREG(file.lstat().st_mode):
            raise BackupError('Backup must contain only ordinary files, without symbolic links.')
    try:
        manifest = read_json(root / 'manifest.json')
        if manifest.get('format') != 1 or manifest.get('image') != image_id:
            raise BackupError('Backup format or server image differs from this release. A tested migration is required.')
        site = manifest.get('site', '')
        if not isinstance(site, str) or not re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,100}', site) or '..' in site:
            raise BackupError('Invalid backup site name.')
        hashes = manifest.get('sha256')
        if not isinstance(hashes, dict) or not hashes or len(hashes) > 16:
            raise BackupError('Invalid backup checksum manifest.')
        if set(hashes) != {p.name for p in root.iterdir()} - {'manifest.json'}:
            raise BackupError('Backup files differ from the checksum manifest.')
        for name, expected in hashes.items():
            if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', name)
                    or Path(name).name != name or name in ('.', '..', 'manifest.json')
                    or '\\' in name or not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected)):
                raise BackupError('Invalid backup checksum manifest.')
            with (root / name).open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                    raise BackupError('Backup checksum mismatch: ' + name)

        def select(suffixes):
            found = [name for name in hashes if name.endswith(suffixes)]
            if len(found) != 1:
                raise BackupError('Backup must contain exactly one ' + suffixes[0])
            return found[0]

        files = dict(database=select(('-database.sql.gz',)),
                     private=select(('-private-files.tgz', '-private-files.tar')),
                     config=select(('site_config_backup.json',)))
        # Public suffix is also a suffix of private-files; choose it explicitly.
        public = [n for n in hashes if n.endswith(('-files.tgz', '-files.tar'))
                  and not n.endswith(('-private-files.tgz', '-private-files.tar'))]
        if len(public) != 1:
            raise BackupError('Backup must contain exactly one public files archive.')
        files['public'] = public[0]
        with (root / files['database']).open('rb') as stream:
            if stream.read(2) != b'\x1f\x8b':
                raise BackupError('Encrypted or unsupported database backup. Decrypt a trusted copy with Frappe first.')
        config = read_json(root / files['config'])
        if config.get('db_type', 'mariadb') != 'mariadb':
            raise BackupError('Only MariaDB backups can be restored by this release.')
        unpacked_bytes = 0
        for visibility in ('public', 'private'):
            with tarfile.open(root / files[visibility], 'r:*') as archive:
                seen = set()
                for member in archive:
                    parts = attachment_path(member, site, visibility)
                    if parts in seen:
                        raise BackupError('Duplicate attachment path in backup.')
                    seen.add(parts)
                    unpacked_bytes += member.size
        return {'manifest': manifest, 'files': files, 'attachment_bytes': unpacked_bytes}
    except (OSError, tarfile.TarError, EOFError) as error:
        raise BackupError('Cannot read complete backup: ' + str(error)) from None


def extract_attachments(root, destination, report):
    """No extractall, links, devices, archive permissions, or overwrite of files."""
    for visibility in ('public', 'private'):
        with tarfile.open(Path(root) / report['files'][visibility], 'r:*') as archive:
            for member in archive:
                parts = attachment_path(member, report['manifest']['site'], visibility)
                target = Path(destination).joinpath(*parts)
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                if member.isdir():
                    target.mkdir(exist_ok=True, mode=0o700)
                else:
                    with archive.extractfile(member) as source, target.open('xb') as output:
                        shutil.copyfileobj(source, output)
                    target.chmod(0o600)
