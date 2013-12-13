"""Automatic code review for changes limited to PEP-8.

Installation:

* in a virtualenv or similar (``virtualenv ./ && source venv/bin/activate``)
* install pydiff and flake8 (``pip install pydiff flake8``)
* cd to Git repository root (``cd django/``)
* run python review8.py FEATURE_BRANCH [REFERENCE_BRANCH]
  ``(python review8.py 1234_pep8 master``)

Reports warnings if:

* some files were created or removed (OK if modifications only)
* some files have been modified and bytecode changed (OK if same bytecode)
* flake8 reports same or more errors (OK if less errors)

As a core developer of some project, pull-requests related to PEP-8 are quite
tricky to review: small changes in code may break code behaviour. And sometimes
tests do not detect problems.
For many changes related to PEP-8, such as spaces and indentation, bytecode
does not change.
This script takes advantage of this fact, compares flake8 reports and compares
bytecode. So that you can focus on readability review.

This script reads Git history to iterate over modified files.
For each file, here is a summary of operations:

* Count PEP-8 violations: ``flake8 PATH | wc -l``
* Compare bytecodes: ``pydiff FILE1 FILE2`` where FILE1 and FILE2 are versions
  of some file in 2 distinct branches.

"""
import argparse
import contextlib
import os
import shutil
import subprocess
import tempfile


class temporary_directory(object):
    """Create, yield, and finally delete a temporary directory.

    >>> with temporary_directory() as directory:
    ... os.path.isdir(directory)
    True
    >>> os.path.exists(directory)
    False

    Deletion of temporary directory is recursive.

    >>> with temporary_directory() as directory:
    ... filename = os.path.join(directory, 'sample.txt')
    ... __ = open(filename, 'w').close()
    ... os.path.isfile(filename)
    True
    >>> os.path.isfile(filename)
    False

    """
    def __enter__(self):
        """Create temporary directory and return its path."""
        self.path = tempfile.mkdtemp()
        return self.path

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        """Remove temporary directory recursively."""
        shutil.rmtree(self.path)


@contextlib.contextmanager
def chdir(path):
    backup = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(backup)


def execute(command, data={}):
    """Execute a shell command.

    Command is a string ; data a dictionnary where values are supposed to be
    strings or integers and not variables or commands.

    Command and data are combined with string format operator.

    Return command's exit code.

    >>> execute_command('echo "%(msg)s"', {'msg': 'Hello world!'})
    Hello world!
    """
    if data:
        command = command % data
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    result = process.wait()
    if result != 0:
        raise Exception('Error while running command "{0}"'.format(command))
    return process.stdout.read()


def flake8_count(path):
    return int(execute('flake8 {path} | wc -l'.format(path=path)).strip())


def git_status_files(repository_dir, start_commit, end_commit, status):
    with chdir(repository_dir):
        output = execute('git diff --name-status {start} {end}'.format(
                         start=start_commit, end=end_commit))
        lines = output.strip().split('\n')
        for line in lines:
            file_status = line[0]
            filename = line[1:].strip()
            if file_status == status:
                yield filename


def git_deleted_files(repository_dir, start_commit, end_commit):
    """Return list of deleted files in Git repository."""
    return git_status_files(repository_dir, start_commit, end_commit, 'D')


def git_modified_files(repository_dir, start_commit, end_commit):
    """Return list of modified files in Git repository."""
    return git_status_files(repository_dir, start_commit, end_commit, 'M')


def git_created_files(repository_dir, start_commit, end_commit):
    """Return list of modified files in Git repository."""
    return git_status_files(repository_dir, start_commit, end_commit, 'A')


def main():
    repository_dir = os.getcwd()
    parser = argparse.ArgumentParser(
        description='Review PEP-8 changes between branches.')
    parser.add_argument(
        'feature',
        action='store',
        nargs='?',
        type=str,
        default=git_branch(repository_dir),
        metavar='FEATURE',
        help='Name of the feature branch')
    parser.add_argument(
        'reference',
        action='store',
        nargs='?',
        default='master',
        type=str,
        metavar='REFERENCE',
        help='Name of the reference branch')
    args = parser.parse_args()
    start_commit = args.reference
    end_commit = args.feature
    git_review8(repository_dir, start_commit, end_commit)


def bytecode_diff(filename, repository_dir, start_commit, end_commit):
    """Return summary of diff between two bytecode versions of filename."""
    with git_checkout(repository_dir, end_commit):
        with temporary_directory() as temp_dir:
            start_file = os.path.join(temp_dir, os.path.basename(filename))
            end_file = os.path.join(repository_dir, filename)
            with git_checkout(repository_dir, start_commit):
                shutil.copy2(end_file, start_file)
            diff = execute('pydiff {0} {1}'.format(start_file, end_file))
            return diff


def git_branch(repository_dir):
    """Return current git branch."""
    with chdir(repository_dir):
        return execute('git rev-parse --abbrev-ref HEAD').strip()


@contextlib.contextmanager
def git_checkout(repository_dir, commit):
    """Checkout repository_dir to commit (revision)."""
    with chdir(repository_dir):
        backup = git_branch(repository_dir)
        if backup != commit:
            try:
                execute('git checkout {commit}'.format(commit=commit))
                yield
            finally:
                execute('git checkout {commit}'.format(commit=backup))
        else:
            yield


def git_review8(repository_dir, start_commit, end_commit):
    """Return number of PEP-8 changes between start_commit and end_commit.

    Raise exception if some changes are not related to PEP-8:

    * files have been added
    * files have been removed
    * modified files have different bytecode

    """
    deleted = list(git_deleted_files(repository_dir, start_commit, end_commit))
    if deleted:
        print('WARNING! Some files were deleted: {0}'.format(deleted))
    created = list(git_created_files(repository_dir, start_commit, end_commit))
    if created:
        print('WARNING! Some files were created: {0}'.format(created))
    modified = git_modified_files(repository_dir, start_commit, end_commit)
    for filename in modified:
        diff = bytecode_diff(filename, repository_dir, start_commit,
                             end_commit)
        if diff:
            print('WARNING! Bytecode of {name} between {start} and {end} '
                  'changed:\n{diff}'.format(
                      name=filename,
                      start=start_commit,
                      end=end_commit,
                      diff=diff))
        else:
            print("OK: no bytecode diff for file {name}".format(name=filename))
    with git_checkout(repository_dir, start_commit):
        start_pep8_report = flake8_count(repository_dir)
        print("{count} flake8 errors in {branch}"
              .format(count=start_pep8_report, branch=start_commit))
    with git_checkout(repository_dir, end_commit):
        end_pep8_report = flake8_count(repository_dir)
        print("{count} flake8 errors in {branch}"
              .format(count=end_pep8_report, branch=end_commit))
    diff = end_pep8_report - start_pep8_report
    if diff < 0:
        print("OK: flake8 reported less errors")
    else:
        print("ERROR: flake8 reported more or equal errors")


if __name__ == '__main__':
    main()
