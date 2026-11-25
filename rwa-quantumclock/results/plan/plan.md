# QAMP plan (development scenarios)

Source: rwa-threatlab census census_raw.json (25 contracts, Etherscan, 2026-11-08). Solver: Optimization terminated successfully. (HiGHS Status 7: Optimal). Objective (expected loss + spend): USD 286.5m.

## ctrl:0x1a694a09494e214a3be3652e4b343b7b81a73ad7

Value at risk USD 2,388m · upgrade_admin · multisig · group Ondo

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q1 [P:ctrl:0x1a694a09494e214a3be3652e4b343b7b81a73ad7].
- The decision window for that boundary closes at the start of 2027 Q3; a later start waits 4 quarter(s) for the next boundary [P:ctrl:0x1a694a09494e214a3be3652e4b343b7b81a73ad7].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- Inventory evidence: access_control_roles [E:abi:0x96f6ef951840721adbf46ac996b59e0235cb985c:access_control_roles].
- Inventory evidence: enumerable_roles [E:abi:0x96f6ef951840721adbf46ac996b59e0235cb985c:enumerable_roles].
- Inventory evidence: upgradeable_proxy [E:abi:0x96f6ef951840721adbf46ac996b59e0235cb985c:upgradeable_proxy].

## role_holder:0x96f6ef951840721adbf46ac996b59e0235cb985c

Value at risk USD 2,388m · role_holder · unobserved_role · group Ondo

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q4 [P:role_holder:0x96f6ef951840721adbf46ac996b59e0235cb985c].
- The decision window for that boundary closes at the start of 2027 Q2; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0x96f6ef951840721adbf46ac996b59e0235cb985c].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: access_control_roles [E:abi:0x96f6ef951840721adbf46ac996b59e0235cb985c:access_control_roles].
- Inventory evidence: enumerable_roles [E:abi:0x96f6ef951840721adbf46ac996b59e0235cb985c:enumerable_roles].
- Inventory evidence: upgradeable_proxy [E:abi:0x96f6ef951840721adbf46ac996b59e0235cb985c:upgradeable_proxy].

## upgrade_admin:0x0990b149e915cb08e2143a5c6f669c907eddc8b0

Value at risk USD 1,920m · upgrade_admin · not_readable · group Spiko

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q1 [P:upgrade_admin:0x0990b149e915cb08e2143a5c6f669c907eddc8b0].
- The decision window for that boundary closes at the start of 2027 Q3; a later start waits 4 quarter(s) for the next boundary [P:upgrade_admin:0x0990b149e915cb08e2143a5c6f669c907eddc8b0].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0x0990b149e915cb08e2143a5c6f669c907eddc8b0:eip2612_permit].
- Inventory evidence: eip712_domain [E:abi:0x0990b149e915cb08e2143a5c6f669c907eddc8b0:eip712_domain].
- Inventory evidence: erc2771_forwarder [E:abi:0x0990b149e915cb08e2143a5c6f669c907eddc8b0:erc2771_forwarder].

## role_holder:0x0990b149e915cb08e2143a5c6f669c907eddc8b0

Value at risk USD 1,920m · role_holder · unobserved_role · group Spiko

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q4 [P:role_holder:0x0990b149e915cb08e2143a5c6f669c907eddc8b0].
- The decision window for that boundary closes at the start of 2027 Q2; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0x0990b149e915cb08e2143a5c6f669c907eddc8b0].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0x0990b149e915cb08e2143a5c6f669c907eddc8b0:eip2612_permit].
- Inventory evidence: eip712_domain [E:abi:0x0990b149e915cb08e2143a5c6f669c907eddc8b0:eip712_domain].
- Inventory evidence: erc2771_forwarder [E:abi:0x0990b149e915cb08e2143a5c6f669c907eddc8b0:erc2771_forwarder].

## upgrade_admin:0x6a9da2d710bb9b700acde7cb81f10f1ff8c89041

Value at risk USD 1,776m · upgrade_admin · not_readable · group BlackRock

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q3 [P:upgrade_admin:0x6a9da2d710bb9b700acde7cb81f10f1ff8c89041].
- The decision window for that boundary closes at the start of 2027 Q1; a later start waits 4 quarter(s) for the next boundary [P:upgrade_admin:0x6a9da2d710bb9b700acde7cb81f10f1ff8c89041].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: external_compliance_module [E:abi:0x6a9da2d710bb9b700acde7cb81f10f1ff8c89041:external_compliance_module].
- Inventory evidence: upgradeable_proxy [E:abi:0x6a9da2d710bb9b700acde7cb81f10f1ff8c89041:upgradeable_proxy].
- Inventory evidence: 0xe01605f6b6dc593b7d2917f4a0940db2a625b09e [E:ctrl:0x6a9da2d710bb9b700acde7cb81f10f1ff8c89041:0xe01605f6b6dc593b7d2917f4a0940db2a625b09e].

## ctrl:0xe01605f6b6dc593b7d2917f4a0940db2a625b09e

Value at risk USD 1,776m · owner_admin · eoa · group BlackRock

- Start the migration in 2027 Q1; with a planned execution time of 1 quarter(s) it takes effect at the renewal boundary 2027 Q2 [P:ctrl:0xe01605f6b6dc593b7d2917f4a0940db2a625b09e].
- The decision window for that boundary closes at the start of 2027 Q1; a later start waits 4 quarter(s) for the next boundary [P:ctrl:0xe01605f6b6dc593b7d2917f4a0940db2a625b09e].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- A single externally owned account controls the token [R:EXP-SINGLE-KEY-ADMIN].
- Inventory evidence: external_compliance_module [E:abi:0x6a9da2d710bb9b700acde7cb81f10f1ff8c89041:external_compliance_module].
- Inventory evidence: upgradeable_proxy [E:abi:0x6a9da2d710bb9b700acde7cb81f10f1ff8c89041:upgradeable_proxy].
- Inventory evidence: 0xe01605f6b6dc593b7d2917f4a0940db2a625b09e [E:ctrl:0x6a9da2d710bb9b700acde7cb81f10f1ff8c89041:0xe01605f6b6dc593b7d2917f4a0940db2a625b09e].

## ctrl:0x49754062e35f7591b93cc4f9915965be89643a65

Value at risk USD 703m · upgrade_admin · multisig · group Backed

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q4 [P:ctrl:0x49754062e35f7591b93cc4f9915965be89643a65].
- The decision window for that boundary closes at the start of 2027 Q2; a later start waits 4 quarter(s) for the next boundary [P:ctrl:0x49754062e35f7591b93cc4f9915965be89643a65].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- Inventory evidence: eip2612_permit [E:abi:0x1aad217b8f78dba5e6693460e8470f8b1a3977f3:eip2612_permit].
- Inventory evidence: signed_parameter_update [E:abi:0x1aad217b8f78dba5e6693460e8470f8b1a3977f3:signed_parameter_update].
- Inventory evidence: upgradeable_proxy [E:abi:0x1aad217b8f78dba5e6693460e8470f8b1a3977f3:upgradeable_proxy].

## role_holder:0x5a0f93d040de44e78f251b03c43be9cf317dcf64

Value at risk USD 578m · role_holder · unobserved_role · group Janus

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q4 [P:role_holder:0x5a0f93d040de44e78f251b03c43be9cf317dcf64].
- The decision window for that boundary closes at the start of 2027 Q2; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0x5a0f93d040de44e78f251b03c43be9cf317dcf64].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0x5a0f93d040de44e78f251b03c43be9cf317dcf64:eip2612_permit].

## upgrade_admin:0x5086bf358635b81d8c47c66d1c8b9e567db70c72

Value at risk USD 377m · upgrade_admin · not_readable · group Re

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q2 [P:upgrade_admin:0x5086bf358635b81d8c47c66d1c8b9e567db70c72].
- The decision window for that boundary closes at the start of 2027 Q4; a later start waits 4 quarter(s) for the next boundary [P:upgrade_admin:0x5086bf358635b81d8c47c66d1c8b9e567db70c72].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: access_control_roles [E:abi:0x5086bf358635b81d8c47c66d1c8b9e567db70c72:access_control_roles].
- Inventory evidence: upgradeable_proxy [E:abi:0x5086bf358635b81d8c47c66d1c8b9e567db70c72:upgradeable_proxy].

## role_holder:0x5086bf358635b81d8c47c66d1c8b9e567db70c72

Value at risk USD 377m · role_holder · unobserved_role · group Re

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q4 [P:role_holder:0x5086bf358635b81d8c47c66d1c8b9e567db70c72].
- The decision window for that boundary closes at the start of 2027 Q2; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0x5086bf358635b81d8c47c66d1c8b9e567db70c72].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: access_control_roles [E:abi:0x5086bf358635b81d8c47c66d1c8b9e567db70c72:access_control_roles].
- Inventory evidence: upgradeable_proxy [E:abi:0x5086bf358635b81d8c47c66d1c8b9e567db70c72:upgradeable_proxy].

## role_holder:0x1aad217b8f78dba5e6693460e8470f8b1a3977f3

Value at risk USD 133m · role_holder · unobserved_role · group Backed

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q3 [P:role_holder:0x1aad217b8f78dba5e6693460e8470f8b1a3977f3].
- The decision window for that boundary closes at the start of 2027 Q1; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0x1aad217b8f78dba5e6693460e8470f8b1a3977f3].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0x1aad217b8f78dba5e6693460e8470f8b1a3977f3:eip2612_permit].
- Inventory evidence: signed_parameter_update [E:abi:0x1aad217b8f78dba5e6693460e8470f8b1a3977f3:signed_parameter_update].
- Inventory evidence: upgradeable_proxy [E:abi:0x1aad217b8f78dba5e6693460e8470f8b1a3977f3:upgradeable_proxy].

## upgrade_admin:0x5fa487bca6158c64046b2813623e20755091da0b

Value at risk USD 117m · upgrade_admin · not_readable · group Theo

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q4 [P:upgrade_admin:0x5fa487bca6158c64046b2813623e20755091da0b].
- The decision window for that boundary closes at the start of 2027 Q2; a later start waits 4 quarter(s) for the next boundary [P:upgrade_admin:0x5fa487bca6158c64046b2813623e20755091da0b].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: access_control_roles [E:abi:0x5fa487bca6158c64046b2813623e20755091da0b:access_control_roles].
- Inventory evidence: upgradeable_proxy [E:abi:0x5fa487bca6158c64046b2813623e20755091da0b:upgradeable_proxy].

## ctrl:0x34e8bb9e0fa50d63bfca1d8e83ddba0d9fd5c062

Value at risk USD 112m · owner_admin · timelock · group Nest

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q1 [P:ctrl:0x34e8bb9e0fa50d63bfca1d8e83ddba0d9fd5c062].
- The decision window for that boundary closes at the start of 2027 Q2; a later start waits 4 quarter(s) for the next boundary [P:ctrl:0x34e8bb9e0fa50d63bfca1d8e83ddba0d9fd5c062].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- Inventory evidence: eip2612_permit [E:abi:0x119dd7daff816f29d7ee47596ae5e4bdc4299165:eip2612_permit].
- Inventory evidence: 0x34e8bb9e0fa50d63bfca1d8e83ddba0d9fd5c062 [E:ctrl:0x119dd7daff816f29d7ee47596ae5e4bdc4299165:0x34e8bb9e0fa50d63bfca1d8e83ddba0d9fd5c062].

## upgrade_admin:0x4c1746a800d224393fe2470c70a35717ed4ea5f1

Value at risk USD 87m · upgrade_admin · not_readable · group Plume

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q2 [P:upgrade_admin:0x4c1746a800d224393fe2470c70a35717ed4ea5f1].
- The decision window for that boundary closes at the start of 2027 Q4; a later start waits 4 quarter(s) for the next boundary [P:upgrade_admin:0x4c1746a800d224393fe2470c70a35717ed4ea5f1].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0x4c1746a800d224393fe2470c70a35717ed4ea5f1:eip2612_permit].
- Inventory evidence: eip712_domain [E:abi:0x4c1746a800d224393fe2470c70a35717ed4ea5f1:eip712_domain].
- Inventory evidence: access_control_roles [E:abi:0x4c1746a800d224393fe2470c70a35717ed4ea5f1:access_control_roles].

## role_holder:0x4c1746a800d224393fe2470c70a35717ed4ea5f1

Value at risk USD 87m · role_holder · unobserved_role · group Plume

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q3 [P:role_holder:0x4c1746a800d224393fe2470c70a35717ed4ea5f1].
- The decision window for that boundary closes at the start of 2027 Q1; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0x4c1746a800d224393fe2470c70a35717ed4ea5f1].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0x4c1746a800d224393fe2470c70a35717ed4ea5f1:eip2612_permit].
- Inventory evidence: eip712_domain [E:abi:0x4c1746a800d224393fe2470c70a35717ed4ea5f1:eip712_domain].
- Inventory evidence: access_control_roles [E:abi:0x4c1746a800d224393fe2470c70a35717ed4ea5f1:access_control_roles].

## upgrade_admin:0x7e2ac793f3e692f388e66c7dc28f739d13b0b71a

Value at risk USD 83m · upgrade_admin · not_readable · group Goldfish

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q3 [P:upgrade_admin:0x7e2ac793f3e692f388e66c7dc28f739d13b0b71a].
- The decision window for that boundary closes at the start of 2027 Q1; a later start waits 4 quarter(s) for the next boundary [P:upgrade_admin:0x7e2ac793f3e692f388e66c7dc28f739d13b0b71a].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: access_control_roles [E:abi:0x7e2ac793f3e692f388e66c7dc28f739d13b0b71a:access_control_roles].
- Inventory evidence: upgradeable_proxy [E:abi:0x7e2ac793f3e692f388e66c7dc28f739d13b0b71a:upgradeable_proxy].

## role_holder:0x7e2ac793f3e692f388e66c7dc28f739d13b0b71a

Value at risk USD 83m · role_holder · unobserved_role · group Goldfish

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q3 [P:role_holder:0x7e2ac793f3e692f388e66c7dc28f739d13b0b71a].
- The decision window for that boundary closes at the start of 2027 Q1; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0x7e2ac793f3e692f388e66c7dc28f739d13b0b71a].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: access_control_roles [E:abi:0x7e2ac793f3e692f388e66c7dc28f739d13b0b71a:access_control_roles].
- Inventory evidence: upgradeable_proxy [E:abi:0x7e2ac793f3e692f388e66c7dc28f739d13b0b71a:upgradeable_proxy].

## upgrade_admin:0x2255718832bc9fd3be1caf75084f4803da14ff01

Value at risk USD 55m · upgrade_admin · not_readable · group VanEck

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q2 [P:upgrade_admin:0x2255718832bc9fd3be1caf75084f4803da14ff01].
- The decision window for that boundary closes at the start of 2027 Q4; a later start waits 4 quarter(s) for the next boundary [P:upgrade_admin:0x2255718832bc9fd3be1caf75084f4803da14ff01].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: external_compliance_module [E:abi:0x2255718832bc9fd3be1caf75084f4803da14ff01:external_compliance_module].
- Inventory evidence: upgradeable_proxy [E:abi:0x2255718832bc9fd3be1caf75084f4803da14ff01:upgradeable_proxy].
- Inventory evidence: 0x59c1eacec450c57dcb9b8725d0f96635c2b676ee [E:ctrl:0x2255718832bc9fd3be1caf75084f4803da14ff01:0x59c1eacec450c57dcb9b8725d0f96635c2b676ee].

## role_holder:0x2255718832bc9fd3be1caf75084f4803da14ff01

Value at risk USD 55m · role_holder · unobserved_role · group VanEck

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q2 [P:role_holder:0x2255718832bc9fd3be1caf75084f4803da14ff01].
- The decision window for that boundary closes at the start of 2027 Q4; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0x2255718832bc9fd3be1caf75084f4803da14ff01].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: external_compliance_module [E:abi:0x2255718832bc9fd3be1caf75084f4803da14ff01:external_compliance_module].
- Inventory evidence: upgradeable_proxy [E:abi:0x2255718832bc9fd3be1caf75084f4803da14ff01:upgradeable_proxy].
- Inventory evidence: 0x59c1eacec450c57dcb9b8725d0f96635c2b676ee [E:ctrl:0x2255718832bc9fd3be1caf75084f4803da14ff01:0x59c1eacec450c57dcb9b8725d0f96635c2b676ee].

## ctrl:0xca3144aad1f75557e68b16c8c7e893112418f13c

Value at risk USD 51m · upgrade_admin · multisig · group Precious

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q3 [P:ctrl:0xca3144aad1f75557e68b16c8c7e893112418f13c].
- The decision window for that boundary closes at the start of 2027 Q1; a later start waits 4 quarter(s) for the next boundary [P:ctrl:0xca3144aad1f75557e68b16c8c7e893112418f13c].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- Inventory evidence: upgradeable_proxy [E:abi:0xc0c17dd08263c16f6b64e772fb9b723bf1344ddf:upgradeable_proxy].
- Inventory evidence: 0xca3144aad1f75557e68b16c8c7e893112418f13c [E:ctrl:0xc0c17dd08263c16f6b64e772fb9b723bf1344ddf:0xca3144aad1f75557e68b16c8c7e893112418f13c].

## ctrl:0xcf355ad32abf378f067fa93a28d96a767feb7377

Value at risk USD 50m · owner_admin · multisig · group USDKG

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q4 [P:ctrl:0xcf355ad32abf378f067fa93a28d96a767feb7377].
- The decision window for that boundary closes at the start of 2027 Q2; a later start waits 4 quarter(s) for the next boundary [P:ctrl:0xcf355ad32abf378f067fa93a28d96a767feb7377].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- Inventory evidence: external_compliance_module [E:abi:0xe820c06321e60d36257c666643fa5436643445e3:external_compliance_module].
- Inventory evidence: 0xcf355ad32abf378f067fa93a28d96a767feb7377 [E:ctrl:0xe820c06321e60d36257c666643fa5436643445e3:0xcf355ad32abf378f067fa93a28d96a767feb7377].

## role_holder:0xe820c06321e60d36257c666643fa5436643445e3

Value at risk USD 50m · role_holder · unobserved_role · group USDKG

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q3 [P:role_holder:0xe820c06321e60d36257c666643fa5436643445e3].
- The decision window for that boundary closes at the start of 2027 Q1; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0xe820c06321e60d36257c666643fa5436643445e3].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: external_compliance_module [E:abi:0xe820c06321e60d36257c666643fa5436643445e3:external_compliance_module].
- Inventory evidence: 0xcf355ad32abf378f067fa93a28d96a767feb7377 [E:ctrl:0xe820c06321e60d36257c666643fa5436643445e3:0xcf355ad32abf378f067fa93a28d96a767feb7377].

## role_holder:0x8c213ee79581ff4984583c6a801e5263418c4b86

Value at risk USD 47m · role_holder · unobserved_role · group Janus

- Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q4 [P:role_holder:0x8c213ee79581ff4984583c6a801e5263418c4b86].
- The decision window for that boundary closes at the start of 2027 Q2; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0x8c213ee79581ff4984583c6a801e5263418c4b86].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0x8c213ee79581ff4984583c6a801e5263418c4b86:eip2612_permit].

## role_holder:0x6a9da2d710bb9b700acde7cb81f10f1ff8c89041

Value at risk USD 1,776m · role_holder · unobserved_role · group BlackRock

- Start the migration in 2027 Q2; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q1 [P:role_holder:0x6a9da2d710bb9b700acde7cb81f10f1ff8c89041].
- The decision window for that boundary closes at the start of 2027 Q3; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0x6a9da2d710bb9b700acde7cb81f10f1ff8c89041].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: external_compliance_module [E:abi:0x6a9da2d710bb9b700acde7cb81f10f1ff8c89041:external_compliance_module].
- Inventory evidence: upgradeable_proxy [E:abi:0x6a9da2d710bb9b700acde7cb81f10f1ff8c89041:upgradeable_proxy].
- Inventory evidence: 0xe01605f6b6dc593b7d2917f4a0940db2a625b09e [E:ctrl:0x6a9da2d710bb9b700acde7cb81f10f1ff8c89041:0xe01605f6b6dc593b7d2917f4a0940db2a625b09e].

## role_holder:0x5fa487bca6158c64046b2813623e20755091da0b

Value at risk USD 117m · role_holder · unobserved_role · group Theo

- Start the migration in 2027 Q2; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q1 [P:role_holder:0x5fa487bca6158c64046b2813623e20755091da0b].
- The decision window for that boundary closes at the start of 2027 Q3; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0x5fa487bca6158c64046b2813623e20755091da0b].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: access_control_roles [E:abi:0x5fa487bca6158c64046b2813623e20755091da0b:access_control_roles].
- Inventory evidence: upgradeable_proxy [E:abi:0x5fa487bca6158c64046b2813623e20755091da0b:upgradeable_proxy].

## upgrade_admin:0x62ca254a363dc3c748e7e955c20447ab5bf06ff7

Value at risk USD 58m · upgrade_admin · not_readable · group iShares

- Start the migration in 2027 Q2; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q1 [P:upgrade_admin:0x62ca254a363dc3c748e7e955c20447ab5bf06ff7].
- The decision window for that boundary closes at the start of 2027 Q3; a later start waits 4 quarter(s) for the next boundary [P:upgrade_admin:0x62ca254a363dc3c748e7e955c20447ab5bf06ff7].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: access_control_roles [E:abi:0x62ca254a363dc3c748e7e955c20447ab5bf06ff7:access_control_roles].
- Inventory evidence: enumerable_roles [E:abi:0x62ca254a363dc3c748e7e955c20447ab5bf06ff7:enumerable_roles].
- Inventory evidence: external_compliance_module [E:abi:0x62ca254a363dc3c748e7e955c20447ab5bf06ff7:external_compliance_module].

## role_holder:0x62ca254a363dc3c748e7e955c20447ab5bf06ff7

Value at risk USD 58m · role_holder · unobserved_role · group iShares

- Start the migration in 2027 Q2; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q1 [P:role_holder:0x62ca254a363dc3c748e7e955c20447ab5bf06ff7].
- The decision window for that boundary closes at the start of 2027 Q3; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0x62ca254a363dc3c748e7e955c20447ab5bf06ff7].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: access_control_roles [E:abi:0x62ca254a363dc3c748e7e955c20447ab5bf06ff7:access_control_roles].
- Inventory evidence: enumerable_roles [E:abi:0x62ca254a363dc3c748e7e955c20447ab5bf06ff7:enumerable_roles].
- Inventory evidence: external_compliance_module [E:abi:0x62ca254a363dc3c748e7e955c20447ab5bf06ff7:external_compliance_module].

## role_holder:0xc0c17dd08263c16f6b64e772fb9b723bf1344ddf

Value at risk USD 51m · role_holder · unobserved_role · group Precious

- Start the migration in 2027 Q2; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q1 [P:role_holder:0xc0c17dd08263c16f6b64e772fb9b723bf1344ddf].
- The decision window for that boundary closes at the start of 2027 Q3; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0xc0c17dd08263c16f6b64e772fb9b723bf1344ddf].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: upgradeable_proxy [E:abi:0xc0c17dd08263c16f6b64e772fb9b723bf1344ddf:upgradeable_proxy].
- Inventory evidence: 0xca3144aad1f75557e68b16c8c7e893112418f13c [E:ctrl:0xc0c17dd08263c16f6b64e772fb9b723bf1344ddf:0xca3144aad1f75557e68b16c8c7e893112418f13c].

## upgrade_admin:0xcbade7d9bdee88411cb6cbcbb29952b742036992

Value at risk USD 244m · upgrade_admin · not_readable · group Spiko

- Start the migration in 2027 Q3; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q1 [P:upgrade_admin:0xcbade7d9bdee88411cb6cbcbb29952b742036992].
- The decision window for that boundary closes at the start of 2027 Q3; a later start waits 4 quarter(s) for the next boundary [P:upgrade_admin:0xcbade7d9bdee88411cb6cbcbb29952b742036992].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0xcbade7d9bdee88411cb6cbcbb29952b742036992:eip2612_permit].
- Inventory evidence: eip712_domain [E:abi:0xcbade7d9bdee88411cb6cbcbb29952b742036992:eip712_domain].
- Inventory evidence: erc2771_forwarder [E:abi:0xcbade7d9bdee88411cb6cbcbb29952b742036992:erc2771_forwarder].

## role_holder:0xae2f842ef90c0d5213259ab82639d5bbf649b08e

Value at risk USD 127m · role_holder · unobserved_role · group Backed

- Start the migration in 2027 Q3; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q3 [P:role_holder:0xae2f842ef90c0d5213259ab82639d5bbf649b08e].
- The decision window for that boundary closes at the start of 2028 Q1; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0xae2f842ef90c0d5213259ab82639d5bbf649b08e].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0xae2f842ef90c0d5213259ab82639d5bbf649b08e:eip2612_permit].
- Inventory evidence: signed_parameter_update [E:abi:0xae2f842ef90c0d5213259ab82639d5bbf649b08e:signed_parameter_update].
- Inventory evidence: upgradeable_proxy [E:abi:0xae2f842ef90c0d5213259ab82639d5bbf649b08e:upgradeable_proxy].

## role_holder:0xfebded1b0986a8ee107f5ab1a1c5a813491deceb

Value at risk USD 116m · role_holder · unobserved_role · group Backed

- Start the migration in 2027 Q3; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q3 [P:role_holder:0xfebded1b0986a8ee107f5ab1a1c5a813491deceb].
- The decision window for that boundary closes at the start of 2028 Q1; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0xfebded1b0986a8ee107f5ab1a1c5a813491deceb].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0xfebded1b0986a8ee107f5ab1a1c5a813491deceb:eip2612_permit].
- Inventory evidence: signed_parameter_update [E:abi:0xfebded1b0986a8ee107f5ab1a1c5a813491deceb:signed_parameter_update].
- Inventory evidence: upgradeable_proxy [E:abi:0xfebded1b0986a8ee107f5ab1a1c5a813491deceb:upgradeable_proxy].

## ctrl:0x3715b2154d2ff4c5b027c7a1f734b53f27bc34f1

Value at risk USD 69m · upgrade_admin · timelock · group Ondo

- Start the migration in 2027 Q3; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2029 Q1 [P:ctrl:0x3715b2154d2ff4c5b027c7a1f734b53f27bc34f1].
- The decision window for that boundary closes at the start of 2028 Q2; a later start waits 4 quarter(s) for the next boundary [P:ctrl:0x3715b2154d2ff4c5b027c7a1f734b53f27bc34f1].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- Inventory evidence: access_control_roles [E:abi:0xace8e719899f6e91831b18ae746c9a965c2119f1:access_control_roles].
- Inventory evidence: enumerable_roles [E:abi:0xace8e719899f6e91831b18ae746c9a965c2119f1:enumerable_roles].
- Inventory evidence: external_compliance_module [E:abi:0xace8e719899f6e91831b18ae746c9a965c2119f1:external_compliance_module].

## role_holder:0xace8e719899f6e91831b18ae746c9a965c2119f1

Value at risk USD 69m · role_holder · unobserved_role · group Ondo

- Start the migration in 2027 Q3; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q4 [P:role_holder:0xace8e719899f6e91831b18ae746c9a965c2119f1].
- The decision window for that boundary closes at the start of 2028 Q2; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0xace8e719899f6e91831b18ae746c9a965c2119f1].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: access_control_roles [E:abi:0xace8e719899f6e91831b18ae746c9a965c2119f1:access_control_roles].
- Inventory evidence: enumerable_roles [E:abi:0xace8e719899f6e91831b18ae746c9a965c2119f1:enumerable_roles].
- Inventory evidence: external_compliance_module [E:abi:0xace8e719899f6e91831b18ae746c9a965c2119f1:external_compliance_module].

## upgrade_admin:0xc273986a91e4bfc543610a5cb5860b7cfefb6cc0

Value at risk USD 59m · upgrade_admin · not_readable · group Spiko

- Start the migration in 2027 Q3; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q1 [P:upgrade_admin:0xc273986a91e4bfc543610a5cb5860b7cfefb6cc0].
- The decision window for that boundary closes at the start of 2027 Q3; a later start waits 4 quarter(s) for the next boundary [P:upgrade_admin:0xc273986a91e4bfc543610a5cb5860b7cfefb6cc0].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0xc273986a91e4bfc543610a5cb5860b7cfefb6cc0:eip2612_permit].
- Inventory evidence: eip712_domain [E:abi:0xc273986a91e4bfc543610a5cb5860b7cfefb6cc0:eip712_domain].
- Inventory evidence: erc2771_forwarder [E:abi:0xc273986a91e4bfc543610a5cb5860b7cfefb6cc0:erc2771_forwarder].

## ctrl:0x59c1eacec450c57dcb9b8725d0f96635c2b676ee

Value at risk USD 55m · owner_admin · eoa · group VanEck

- Start the migration in 2027 Q3; with a planned execution time of 1 quarter(s) it takes effect at the renewal boundary 2028 Q1 [P:ctrl:0x59c1eacec450c57dcb9b8725d0f96635c2b676ee].
- The decision window for that boundary closes at the start of 2027 Q4; a later start waits 4 quarter(s) for the next boundary [P:ctrl:0x59c1eacec450c57dcb9b8725d0f96635c2b676ee].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- A single externally owned account controls the token [R:EXP-SINGLE-KEY-ADMIN].
- Inventory evidence: external_compliance_module [E:abi:0x2255718832bc9fd3be1caf75084f4803da14ff01:external_compliance_module].
- Inventory evidence: upgradeable_proxy [E:abi:0x2255718832bc9fd3be1caf75084f4803da14ff01:upgradeable_proxy].
- Inventory evidence: 0x59c1eacec450c57dcb9b8725d0f96635c2b676ee [E:ctrl:0x2255718832bc9fd3be1caf75084f4803da14ff01:0x59c1eacec450c57dcb9b8725d0f96635c2b676ee].

## role_holder:0xcbade7d9bdee88411cb6cbcbb29952b742036992

Value at risk USD 244m · role_holder · unobserved_role · group Spiko

- Start the migration in 2028 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q4 [P:role_holder:0xcbade7d9bdee88411cb6cbcbb29952b742036992].
- The decision window for that boundary closes at the start of 2028 Q2; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0xcbade7d9bdee88411cb6cbcbb29952b742036992].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0xcbade7d9bdee88411cb6cbcbb29952b742036992:eip2612_permit].
- Inventory evidence: eip712_domain [E:abi:0xcbade7d9bdee88411cb6cbcbb29952b742036992:eip712_domain].
- Inventory evidence: erc2771_forwarder [E:abi:0xcbade7d9bdee88411cb6cbcbb29952b742036992:erc2771_forwarder].

## role_holder:0x90a2a4c76b5d8c0bc892a69ea28aa775a8f2dd48

Value at risk USD 73m · role_holder · unobserved_role · group Backed

- Start the migration in 2028 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q3 [P:role_holder:0x90a2a4c76b5d8c0bc892a69ea28aa775a8f2dd48].
- The decision window for that boundary closes at the start of 2028 Q1; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0x90a2a4c76b5d8c0bc892a69ea28aa775a8f2dd48].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0x90a2a4c76b5d8c0bc892a69ea28aa775a8f2dd48:eip2612_permit].
- Inventory evidence: signed_parameter_update [E:abi:0x90a2a4c76b5d8c0bc892a69ea28aa775a8f2dd48:signed_parameter_update].
- Inventory evidence: upgradeable_proxy [E:abi:0x90a2a4c76b5d8c0bc892a69ea28aa775a8f2dd48:upgradeable_proxy].

## role_holder:0xa753a7395cae905cd615da0b82a53e0560f250af

Value at risk USD 70m · role_holder · unobserved_role · group Backed

- Start the migration in 2028 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q3 [P:role_holder:0xa753a7395cae905cd615da0b82a53e0560f250af].
- The decision window for that boundary closes at the start of 2028 Q1; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0xa753a7395cae905cd615da0b82a53e0560f250af].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0xa753a7395cae905cd615da0b82a53e0560f250af:eip2612_permit].
- Inventory evidence: signed_parameter_update [E:abi:0xa753a7395cae905cd615da0b82a53e0560f250af:signed_parameter_update].
- Inventory evidence: upgradeable_proxy [E:abi:0xa753a7395cae905cd615da0b82a53e0560f250af:upgradeable_proxy].

## role_holder:0xc273986a91e4bfc543610a5cb5860b7cfefb6cc0

Value at risk USD 59m · role_holder · unobserved_role · group Spiko

- Start the migration in 2028 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2028 Q4 [P:role_holder:0xc273986a91e4bfc543610a5cb5860b7cfefb6cc0].
- The decision window for that boundary closes at the start of 2028 Q2; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0xc273986a91e4bfc543610a5cb5860b7cfefb6cc0].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0xc273986a91e4bfc543610a5cb5860b7cfefb6cc0:eip2612_permit].
- Inventory evidence: eip712_domain [E:abi:0xc273986a91e4bfc543610a5cb5860b7cfefb6cc0:eip712_domain].
- Inventory evidence: erc2771_forwarder [E:abi:0xc273986a91e4bfc543610a5cb5860b7cfefb6cc0:erc2771_forwarder].

## role_holder:0xe92f673ca36c5e2efd2de7628f815f84807e803f

Value at risk USD 66m · role_holder · unobserved_role · group Backed

- Start the migration in 2028 Q3; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2029 Q3 [P:role_holder:0xe92f673ca36c5e2efd2de7628f815f84807e803f].
- The decision window for that boundary closes at the start of 2029 Q1; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0xe92f673ca36c5e2efd2de7628f815f84807e803f].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0xe92f673ca36c5e2efd2de7628f815f84807e803f:eip2612_permit].
- Inventory evidence: signed_parameter_update [E:abi:0xe92f673ca36c5e2efd2de7628f815f84807e803f:signed_parameter_update].
- Inventory evidence: upgradeable_proxy [E:abi:0xe92f673ca36c5e2efd2de7628f815f84807e803f:upgradeable_proxy].

## role_holder:0x8ad3c73f833d3f9a523ab01476625f269aeb7cf0

Value at risk USD 66m · role_holder · unobserved_role · group Backed

- Start the migration in 2028 Q4; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2029 Q3 [P:role_holder:0x8ad3c73f833d3f9a523ab01476625f269aeb7cf0].
- The decision window for that boundary closes at the start of 2029 Q1; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0x8ad3c73f833d3f9a523ab01476625f269aeb7cf0].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0x8ad3c73f833d3f9a523ab01476625f269aeb7cf0:eip2612_permit].
- Inventory evidence: signed_parameter_update [E:abi:0x8ad3c73f833d3f9a523ab01476625f269aeb7cf0:signed_parameter_update].
- Inventory evidence: upgradeable_proxy [E:abi:0x8ad3c73f833d3f9a523ab01476625f269aeb7cf0:upgradeable_proxy].

## role_holder:0xc845b2894dbddd03858fd2d643b4ef725fe0849d

Value at risk USD 52m · role_holder · unobserved_role · group Backed

- Start the migration in 2029 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2029 Q3 [P:role_holder:0xc845b2894dbddd03858fd2d643b4ef725fe0849d].
- The decision window for that boundary closes at the start of 2029 Q1; a later start waits 4 quarter(s) for the next boundary [P:role_holder:0xc845b2894dbddd03858fd2d643b4ef725fe0849d].
- The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- It is deprecated after 2030-12-31 [R:NIST8547-DEPRECATE].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-FATF-R11].
- The anchor signs compliance records that must remain evidence for 5 years [R:RET-EU-AMLD-40].
- The anchor signs compliance records that must remain evidence for 6 years [R:RET-US-SEC-17A4].
- Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-UNKNOWN].
- The key holders could not be read on-chain and must be identified first [R:EXP-DISCOVERY-INCOMPLETE].
- Inventory evidence: eip2612_permit [E:abi:0xc845b2894dbddd03858fd2d643b4ef725fe0849d:eip2612_permit].
- Inventory evidence: signed_parameter_update [E:abi:0xc845b2894dbddd03858fd2d643b4ef725fe0849d:signed_parameter_update].
- Inventory evidence: upgradeable_proxy [E:abi:0xc845b2894dbddd03858fd2d643b4ef725fe0849d:upgradeable_proxy].
