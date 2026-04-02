# EXAMPLES

Bu klasör, RL odaklı MCP surface'in gerçek bir kodlama akışında nasıl davrandığını **zor RL bug ailelerini temsil eden 10 deterministik mikro-senaryo** üstünden canlı olarak gösterir.

## Demo akışı

Her seeded bug vakasında şu zincir gerçekten çalışır:

1. Geliştirici hatalı RL kodunu yazar.
2. Script gerçekten çalışır ve gerçekten `AssertionError` ile patlar.
3. Runner gerçek MCP server'ı stdio üzerinden başlatır.
4. `issue_record_resolution` ile izole demo DB'sine doğrulanmış RL bug pattern'i seed edilir.
5. `issue_match` + `issue_get` + `issue_guardrails` + `issue_feedback` canlı çağrılır.
6. Sistem doğru RL fix yönüne gidiyor mu ölçülür.

Ayrıca iki fixed kontrol vakası da çalıştırılır; hata olmadığı için MCP yoluna girilmez.
Not: fixed tarafta şu an yalnızca **2 kontrol vakası** vardır; bu demo tüm bug aileleri için tam fix-doğrulama matrisi sunduğunu iddia etmez.

## Temsil edilen zor RL bug aileleri

1. Q-learning terminal bootstrap leak
2. DQN target-network leakage
3. N-step return missing done mask
4. PPO clipped surrogate max-vs-min bug
5. GAE terminal mask omission
6. Actor-critic returns-vs-advantage bug
7. SAC alpha / temperature sign bug
8. TD3 target smoothing clip omission
9. TD3 policy-delay schedule bug
10. Off-policy importance-weight omission (V-trace style)

## Ölçülen metrikler

- `buggy_detection_recall`
- `routing_accuracy`
- `fixed_non_trigger_rate`
- `mean_issue_match_latency_ms`
- `mean_score_uplift_after_feedback`
- vaka bazlı top match, fix ve guardrail bilgisi

## Dürüstlük notu

- Bu demo, pattern'leri önce **izole demo veritabanına seed ederek** çalışır.
- Dolayısıyla bu akış, tamamen boş memory ile sıfırdan genelleme testi değildir.
- `fixed_non_trigger_rate`, abstain benchmark'ı değil; fixed script hata vermediği için orchestrator'ın MCP yoluna hiç girmeme oranıdır.

## Çalıştırma

```bash
PYTHONPATH=src .venv/bin/python EXAMPLES/run_rl_scenarios.py
```

## Test

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/integration/test_examples_rl_scenarios.py
```

## Teknik not

Bu demo doğrudan gerçek MCP stdio hattını kullanır:

- `python -m rl_developer_memory.server`
- `mcp.client.stdio`
- `ClientSession.call_tool(...)`

Yani burada gerçekten RL MCP tetiklenir; lokal direct-call kullanılmaz.
