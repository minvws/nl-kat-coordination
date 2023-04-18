# Pull Request Template
````
### Changes
_Please describe the essence of this PR in a few sentences. Mention any breaking changes or required configuration steps._

### Issue link
_Please add a link to the issue. If there is no issue for this PR, please add it to the project board directly._

### Proof
_Please add some proof of your working change here, unless this is not required (e.g. this PR is trivial)._

---
## Checklists for authors:

### Code Checklist
- [ ] This PR only contains functionality relevant to the issue; tickets have been created for newly discovered issues.
- [ ] I have written unit tests for the changes or fixes I made.
- [ ] For any non-trivial functionality, I have added integration and/or end-to-end tests.
- [ ] I have performed a self-review of my code and refactored it to the best of my abilities.


### Communication
- [ ] I have informed others of any required `.env` changes files if required and changed the `.env-dist` accordingly.
- [ ] I have made corresponding changes to the documentation, if necessary.

---
## Checklist for code reviewers:
- [ ] The code does not violate Model-View-Template and our other architectural principles.
- [ ] The code prioritizes readability over performance where appropriate.
- [ ] The code does not bypass authentication or security mechanisms.
- [ ] The code does not introduce any dependency on a library that has not been properly vetted.
- [ ] The code contains docstrings, comments, and documentation where needed.

---
## Checklist for QA:
- [ ] I have checked out this branch, and successfully ran a fresh `make kat`.
- [ ] I confirmed that there are no unintended functional regressions in this branch:
    - [ ] I have managed to pass the onboarding flow
    - [ ] Objects and Findings are created properly
    - [ ] Tasks are created and completed properly
- [ ] I confirmed that the PR's advertised `feature` or `hotfix` works as intended.

### What works:
* _bullet point + screenshot (if useful) per tested functionality_

### What doesn't work:
* _bullet point + screenshot (if useful) per tested functionality_

### Bug or feature?:
* _bullet point + screenshot (if useful) if it is unclear whether something is a bug or an intended feature._
````
