import os
import pathlib
import shutil
from pprint import pprint
from typing import Dict

import securesystemslib as sslib
import tuf
import tuf.repository_tool as repo_tool
import tuf.scripts.repo as tuf_repo

default_trust_dir = pathlib.Path.joinpath(pathlib.Path.home(), '.pysigny')
keystore_dir = 'private'
root_key_name = 'root_key'
targets_key_name = 'targets_key'
snapshot_key_name = 'snapshot_key'
timestamp_key_name = 'timestamp_key'
metadata_staged_dir = 'metadata.staged'
metadata_dir = 'metadata'
targets_dir = 'targets'


class TUFKey:
    private: None
    public: None
    passphrase: None


keys: Dict[str, TUFKey] = {
    root_key_name: TUFKey,
    targets_key_name: TUFKey,
    snapshot_key_name: TUFKey,
    timestamp_key_name: TUFKey
}


def init_repo(target, name, trustdir):
    repo_path = os.path.join(trustdir, name)
    repository = repo_tool.create_new_repository(repo_path)
    create_and_set_keys(repository, name, trustdir)
    # write_repo(repository, name, trustdir)
    # add_target_to_repository(repository, target, name, trustdir)


def create_and_set_keys(repository, name, trustdir):
    for k, v in keys.items():
        p = os.environ.get(k.upper() + '_PASSPHRASE')
        if p == None:
            v.passphrase = sslib.interface.get_password(
                prompt='Enter password for {0}: '.format(k), confirm=True)
        else:
            v.passphrase = p

        repo_tool.generate_and_write_ecdsa_keypair(os.path.join(
            trustdir, name, keystore_dir, k), password=v.passphrase)

        v.private = tuf_repo.import_privatekey_from_file(
            os.path.join(trustdir, name, keystore_dir, k), v.passphrase)

        v.public = tuf_repo.import_publickey_from_file(
            os.path.join(trustdir, name, keystore_dir, k) + '.pub')

    pprint(vars(keys[root_key_name]))

    repository.root.add_verification_key(keys[root_key_name].public)
    repository.targets.add_verification_key(keys[targets_key_name].public)
    repository.snapshot.add_verification_key(keys[snapshot_key_name].public)
    repository.timestamp.add_verification_key(keys[timestamp_key_name].public)

    repository.root.load_signing_key(keys[root_key_name].private)
    repository.targets.load_signing_key(keys[targets_key_name].private)
    repository.snapshot.load_signing_key(keys[snapshot_key_name].private)
    repository.timestamp.load_signing_key(keys[timestamp_key_name].private)


def write_repo(repository, name, trustdir):
    staged_meta = os.path.join(trustdir, name, metadata_staged_dir)
    meta = os.path.join(trustdir, name, metadata_dir)
    shutil.rmtree(meta, ignore_errors=True)
    shutil.copytree(staged_meta, meta)

    repository.writeall(consistent_snapshot=True)


def add_target_to_repository(repository, target, name, trustdir):
    print('REPOSITORY: ')
    pprint(vars(repository))
    targets_path = os.path.join(trustdir, name, targets_dir)
    sslib.util.ensure_parent_dir(
        os.path.join(targets_path, target))
    shutil.copy(target, os.path.join(targets_path, target))

    # TODO
    #
    # populate custom object with in-toto metatada
    custom = {}

    # TODO
    #
    # allow passing a different role?
    roleinfo = tuf.roledb.get_roleinfo(
        "targets", repository_name=repository._repository_name)

    if target not in roleinfo['paths']:
        print('Adding new target: ' + repr(target))
        roleinfo['paths'].update({target: custom})

    else:
        print('Replacing target: ' + repr(target))
        roleinfo['paths'].update({target: custom})

    pprint(roleinfo)
    tuf.roledb.update_roleinfo("targets", roleinfo,
                               mark_role_as_dirty=True, repository_name=repository._repository_name)

    snapshot = tuf.roledb.get_roleinfo(
        'root', repository_name=repository._repository_name)['consistent_snapshot']
    repository.targets.load_signing_key(keys[targets_key_name].private)
    repository.write('targets', consistent_snapshot=snapshot,
                     increment_version_number=True)
