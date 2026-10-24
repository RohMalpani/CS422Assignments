# AI usage

Document how AI tools were used and what the group verified independently.

AI helped draft the congestion-control pseudocode and initial Linux module.
The group must review the code, verify compilation and behavior on its kernel,
and independently interpret the four-algorithm measurements before submission.

Claude Code was used to set up the WSL2 build environment (kernel source,
`Module.symvers`, vermagic fix), build and load the module, and check that a
socket can select it. The group then recorded a matched four-algorithm run.
Codex helped audit the saved CSVs, generate the comparison plots, and draft the
report. The group must review the implementation and interpretation and
demonstrate the build and load on its own kernel during grading.
