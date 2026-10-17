# AI usage acknowledgment — Assignment 2

Claude Code (Anthropic) was used as a coding assistant, step by step, for Part 1:
- explaining the iperf3 control/data protocol and drafting `iperf3_client.py`;
- drafting the `struct tcp_info` decoder (`goodput.py`), which we verified against C `offsetof()`;
- boilerplate for the experiment driver, plotting and summary tables;
- debugging and testing runs against public iperf3 servers in WSL2.

Each step was explained, tested and logged in `DECISIONS.md`; group members are responsible for understanding and being able to explain all code.
