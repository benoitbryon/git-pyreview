############
git-pyreview
############

Utilities to compare Python-specific changes within Git repositories.

.. warning::

   This project is a proof of concept... Features are not implemented yet!


********
Use case
********

This project was initiated to help Django developers to review pull-requests
related to PEP-8.

When you review changes related to PEP-8, you have to make sure code is not
broken, i.e. behaviour is the same. Since most changes related to PEP-8 are
easy to apply, code review is long, compared to "do-it-myself".

The idea is to make code review easier, especially if changes are minor:

* highlight bytecode changes: where bytecode does not change, you can focus on
  readability changes.

* highlight changes in flake8 reports: make sure coding style was improved.

Of course, some changes related to PEP-8 alter bytecode, but some does not. As
an example, whitespace changes should be easy to review.


********
Commands
********

git-pydiff
==========

``git-pydiff`` does bytecode comparison between 2 revisions.

git-pystatus
============

``git-pystatus`` highlights Python bytecode changes.

git-pep8diff
============

``git-pep8diff`` does PEP-8 comparison (using `flake8`_) between 2 revisions.
It highlights PEP-8 improvements/regressions.

git-pep8status
==============

``git-pep8status`` highlights changes related to PEP-8.
