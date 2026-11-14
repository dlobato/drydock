# Single 100-switch qualification attempt

The user approved one live attempt with four private `n2-standard-32` workers and one disposable runner.
The trusted workflow revision is `43eb6a4b0916a6e4903486555f385a65d19ee8d8` from PR #29.
The selected fabric contains two spines, 98 leaves, 49 MLAG pairs, and 294 links.
The offline preparation produced 1,088 required ANTA entries.

This attempt keeps the existing 900-second startup bound and the 30-minute default lab lifetime.
Removal starts within 90 minutes of the first temporary worker allocation.
It permits no automatic retry, capacity increase, or expiry extension.
The operator preserves the shared cluster and its original system pool.

Live results and independent cleanup evidence remain pending.
Task 9.1 remains unchecked until the complete acceptance criteria pass.
Tasks 9.2 through 9.4 retain concurrency, failure-path, and provider qualification.

See the [qualification plan](scale-qualification.md) for the approved resource and evidence boundaries.
