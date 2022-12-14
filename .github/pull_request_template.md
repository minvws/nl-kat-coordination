## Changes
_Please describe the essence of this PR in a few sentences._

## Issue ticket number and link
_Please paste a link to the issue on the project board here. Alternatively, if there was no submitted issue prior to this PR, you may add this PR to the project board directly._

## Proof
_Please paste some screenshots or other proof of your (working) change here. If you feel that this is not required (e.g. this PR is trivial), note that here._

## Extra instructions for others
_This section may be skipped or omitted. Uncomment and answer the below questions if relevant._

<!---
- Does this PR introduce or depend on API-incompatible changes? If yes: what do other users/developers need to do or confirm before merging?
- Does this PR depend on a specific version of a library?
- Does this PR depend on any other pending PR's?
- Does this PR require config, setup, or `.env` changes?
-->

## Checklist for author(s):
- [ ] This PR comes from a `feature` or `hotfix` branch, in line with our git branching strategy;
- [ ] This PR is "bite-sized" and only focuses on a single issue, problem, or feature;
- [ ] If a non-trivial PR: This PR is properly linked to the project board (either directly or via an issue);
- [ ] If a non-trivial PR: I have added screenshots or some other proof that my code does what it is supposed to do;
- [ ] I am not reinventing the wheel: there is no high-quality library that already has this feature;
- [ ] I have changed the example `.env` files if I added, removed, or changed any config options, and I have informed others that they need to modify their `.env` files if required;
- [ ] I have performed a self-review of my own code;
- [ ] I have commented my code, particularly in hard-to-understand areas;
- [ ] I have made corresponding changes to the documentation, if necessary;
- [ ] I have written unit, integration, and end-to-end tests for the change that I made;


```
## Checklist for functional reviewer(s):
- [ ] If a non-trivial PR: This PR is properly linked to an issue on the project board;
- [ ] I have checked out this branch, and successfully ran `make kat`;
- [ ] I have ran `make test-rf` and all end-to-end Robot Framework tests pass;
- [ ] I confirmed that the PR's advertised `feature` or `hotfix` works as intended;
- [ ] I confirmed that there are no unintended functional regressions in this branch;

### What works:
* _bullet point + screenshot (if useful) per tested functionality_

### What doesn't work:
* _bullet point + screenshot (if useful) per tested functionality_

### Bug or feature?:
* _bullet point + screenshot (if useful) if it is unclear whether something is a bug or an intended feature._
```

```
## Checklist for code reviewer(s):
- [ ] The code passes the CI tests and linters;
- [ ] The code does not bypass authentication or security mechanisms;
- [ ] The code does not introduce any dependency on a library that has not been properly vetted;
- [ ] The code does not violate Model-View-Template and our other architectural principles;
- [ ] The code contains docstrings, comments, and documentation where needed;
- [ ] The code prioritizes readability over performance where appropriate;
- [ ] The code conforms to our agreed coding standards.
```
