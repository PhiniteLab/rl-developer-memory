# RL MCP hard scenario demo

- Generated at: `2026-04-02T21:55:08+00:00`
- Transport: `mcp_stdio` via `rl-developer-memory`
- Overall status: **passed**
- Buggy cases: `10`
- Fixed cases: `2`
- Buggy detection recall: `1.0`
- Fixed non-trigger rate: `1.0`
- Routing accuracy: `1.0`
- Mean issue_match latency (ms): `78.116`
- Mean score uplift after feedback: `0.0141`

## Cases
### Buggy Q-learning terminal bootstrap
- Kind: `buggy`
- Failure detected: `True`
- Error excerpt: `AssertionError: Q-learning target bootstraps through terminal state; expected reward-only target when done=True.`
- MCP triggered: `True`
- MCP decision: `match`
- Top title: `Q-learning terminal target bootstraps after done=True`
- Canonical fix: `Mask the Bellman bootstrap with (1 - done) so terminal transitions only use the immediate reward.`
- Guardrail count: `3`
- Score before feedback: `0.828`
- Score after feedback: `0.855`
- Route OK: **True**

### Buggy DQN target-network leakage
- Kind: `buggy`
- Failure detected: `True`
- Error excerpt: `AssertionError: DQN target uses online-network bootstrap value instead of detached target-network value.`
- MCP triggered: `True`
- MCP decision: `match`
- Top title: `DQN TD target leaks online-network values instead of detached target-network values`
- Canonical fix: `Select the greedy action with the online network if desired, but evaluate the bootstrap value with the detached target-network outputs.`
- Guardrail count: `3`
- Score before feedback: `0.906`
- Score after feedback: `0.932`
- Route OK: **True**

### Buggy n-step return terminal masking
- Kind: `buggy`
- Failure detected: `True`
- Error excerpt: `AssertionError: N-step return bootstraps past a terminal transition; expected terminal mask to stop recursion.`
- MCP triggered: `True`
- MCP decision: `match`
- Top title: `N-step return bootstraps beyond terminal transition`
- Canonical fix: `Apply the done mask inside the n-step recursion so the bootstrap tail is zeroed after the first terminal transition.`
- Guardrail count: `3`
- Score before feedback: `0.872`
- Score after feedback: `0.898`
- Route OK: **True**

### Buggy PPO clipped surrogate
- Kind: `buggy`
- Failure detected: `True`
- Error excerpt: `AssertionError: PPO clipped objective uses max instead of min for positive advantages.`
- MCP triggered: `True`
- MCP decision: `match`
- Top title: `PPO clipped surrogate uses max instead of min`
- Canonical fix: `For positive advantages, compute the PPO surrogate with the minimum of unclipped and clipped terms so the trust-region style clip is respected.`
- Guardrail count: `3`
- Score before feedback: `0.999`
- Score after feedback: `0.999`
- Route OK: **True**

### Buggy GAE terminal masking
- Kind: `buggy`
- Failure detected: `True`
- Error excerpt: `AssertionError: GAE recursion propagates advantage across terminal boundary because done mask is ignored.`
- MCP triggered: `True`
- MCP decision: `match`
- Top title: `GAE recursion ignores terminal mask`
- Canonical fix: `Multiply both next-value and recursive advantage terms by the terminal mask before propagating GAE.`
- Guardrail count: `3`
- Score before feedback: `0.862`
- Score after feedback: `0.888`
- Route OK: **True**

### Buggy actor-critic returns-vs-advantage
- Kind: `buggy`
- Failure detected: `True`
- Error excerpt: `AssertionError: Actor-critic policy loss is using returns instead of advantages; subtract critic values before policy update.`
- MCP triggered: `True`
- MCP decision: `match`
- Top title: `Actor-critic policy update uses returns instead of advantages`
- Canonical fix: `Compute policy loss from advantages (returns - critic values) instead of raw returns.`
- Guardrail count: `3`
- Score before feedback: `0.99`
- Score after feedback: `0.999`
- Route OK: **True**

### Buggy SAC temperature sign
- Kind: `buggy`
- Failure detected: `True`
- Error excerpt: `AssertionError: SAC temperature update uses the wrong sign; expected target_entropy - observed_entropy.`
- MCP triggered: `True`
- MCP decision: `match`
- Top title: `SAC temperature update uses the wrong entropy residual sign`
- Canonical fix: `Form the SAC temperature residual as target_entropy - observed_entropy so the alpha update moves in the correct exploration-restoring direction.`
- Guardrail count: `3`
- Score before feedback: `0.999`
- Score after feedback: `0.999`
- Route OK: **True**

### Buggy TD3 target smoothing clip
- Kind: `buggy`
- Failure detected: `True`
- Error excerpt: `AssertionError: TD3 target policy smoothing misses action clipping and exceeds action bounds.`
- MCP triggered: `True`
- MCP decision: `match`
- Top title: `TD3 target policy smoothing misses action clipping`
- Canonical fix: `After adding TD3 smoothing noise, clip the target action back to the environment action bounds before computing critic targets.`
- Guardrail count: `3`
- Score before feedback: `0.999`
- Score after feedback: `0.999`
- Route OK: **True**

### Buggy TD3 policy-delay schedule
- Kind: `buggy`
- Failure detected: `True`
- Error excerpt: `AssertionError: TD3 actor update ignores policy_delay and runs on every critic step.`
- MCP triggered: `True`
- MCP decision: `match`
- Top title: `TD3 actor update ignores delayed policy schedule`
- Canonical fix: `Gate the TD3 actor update with the configured policy_delay so the actor is updated only on delayed critic steps.`
- Guardrail count: `3`
- Score before feedback: `0.999`
- Score after feedback: `0.999`
- Route OK: **True**

### Buggy off-policy importance correction
- Kind: `buggy`
- Failure detected: `True`
- Error excerpt: `AssertionError: Off-policy correction omits clipped importance weights in the actor update.`
- MCP triggered: `True`
- MCP decision: `match`
- Top title: `Off-policy correction omits clipped importance weights`
- Canonical fix: `Multiply the off-policy actor correction term by the clipped importance weights before applying the update.`
- Guardrail count: `3`
- Score before feedback: `0.875`
- Score after feedback: `0.902`
- Route OK: **True**

### Fixed Q-learning terminal handling
- Kind: `fixed`
- Failure detected: `False`
- MCP triggered: `False`
- Route OK: **True**

### Fixed actor-critic advantage usage
- Kind: `fixed`
- Failure detected: `False`
- MCP triggered: `False`
- Route OK: **True**

