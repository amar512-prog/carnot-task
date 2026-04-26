# Recent-Event Clustering Demo

A distributable interview demo that continuously ingests text events, clusters similar recent events, exposes live decisions over an API plus SSE stream, and includes replay, reset, and threshold-calibration workflows.

## Stack
- FastAPI
- PostgreSQL + pgvector
- Python CLI with Typer + Rich
- Docker Compose for one-command local startup

## Quick Start
```bash
docker compose up --build
```

### run evaluation
```bash
docker compose exec api python ./scripts/evaluate.py ./data/baseline_story.jsonl
```
#### output
```bash
root@7a9c7617f233:/app#  python ./scripts/evaluate.py ./data/baseline_story.jsonl 
Running approach 1 (Score Partition)...
2026-04-26 10:26:54,773 [INFO] waiting to acquire replay maintenance lock 442001
2026-04-26 10:26:54,774 [INFO] acquired replay maintenance lock 442001 (releases with transaction)
2026-04-26 10:26:54,820 [INFO] waiting to acquire replay maintenance lock 442001
2026-04-26 10:26:54,820 [INFO] acquired replay maintenance lock 442001 (releases with transaction)
2026-04-26 10:27:00,949 [INFO] Use pytorch device_name: cpu
2026-04-26 10:27:00,949 [INFO] Load pretrained SentenceTransformer: codefuse-ai/F2LLM-v2-0.6B
2026-04-26 10:27:14,384 [INFO] 2 prompts are loaded, with the keys: ['query', 'document']
2026-04-26 10:27:16,115 [INFO] Use pytorch device: cpu
2026-04-26 10:27:16,125 [INFO] starting to embed the event id evt-1001 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  2.19it/s]
2026-04-26 10:27:16,591 [INFO] completed to embed the event id evt-1001 using 1 embeddings
2026-04-26 10:27:16,593 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:27:16,594 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:27:16,597 [INFO] in case of approach 1, draft mention if added new event: created draft cluster ca966df1-7d3a-4ae0-b887-1b8c1df8e9ae
2026-04-26 10:27:16,597 [INFO] cluster assigned, event evt-1001 -> cluster ca966df1-7d3a-4ae0-b887-1b8c1df8e9ae (created_new_cluster)
2026-04-26 10:27:16,597 [INFO] starting to embed the event id evt-1002 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.47it/s]
2026-04-26 10:27:16,783 [INFO] completed to embed the event id evt-1002 using 1 embeddings
2026-04-26 10:27:16,784 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:27:16,784 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:27:16,788 [INFO] in case of approach 1, draft mention if added new event: created draft cluster 4d4e0b02-447e-45ce-b9a9-6c471cde6920
2026-04-26 10:27:16,788 [INFO] cluster assigned, event evt-1002 -> cluster 4d4e0b02-447e-45ce-b9a9-6c471cde6920 (created_new_cluster)
2026-04-26 10:27:16,788 [INFO] starting to embed the event id evt-1003 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  6.00it/s]
2026-04-26 10:27:16,957 [INFO] completed to embed the event id evt-1003 using 1 embeddings
2026-04-26 10:27:16,959 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:27:16,959 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:27:16,962 [INFO] starting to embed the event id evt-1004 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.97it/s]
2026-04-26 10:27:17,132 [INFO] completed to embed the event id evt-1004 using 1 embeddings
2026-04-26 10:27:17,133 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:27:17,133 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:27:17,138 [INFO] in case of approach 1, draft mention if added new event: created draft cluster 0c39dc81-e5c8-498b-82e0-ccc07179cceb
2026-04-26 10:27:17,138 [INFO] cluster assigned, event evt-1004 -> cluster 0c39dc81-e5c8-498b-82e0-ccc07179cceb (created_new_cluster)
2026-04-26 10:27:17,138 [INFO] starting to embed the event id evt-1005 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  6.08it/s]
2026-04-26 10:27:17,305 [INFO] completed to embed the event id evt-1005 using 1 embeddings
2026-04-26 10:27:17,306 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:27:17,306 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:27:17,310 [INFO] in case of approach 1, draft mention if added new event: created draft cluster b204e7cf-9963-44de-9779-211560c17cea
2026-04-26 10:27:17,310 [INFO] cluster assigned, event evt-1005 -> cluster b204e7cf-9963-44de-9779-211560c17cea (created_new_cluster)
2026-04-26 10:27:17,311 [INFO] starting to embed the event id evt-1006 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  6.02it/s]
2026-04-26 10:27:17,479 [INFO] completed to embed the event id evt-1006 using 1 embeddings
2026-04-26 10:27:17,481 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:27:17,481 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:27:17,486 [INFO] in case of approach 1, draft mention if added new event: created draft cluster de7c545b-b23c-47da-9f15-2f45a386db26
2026-04-26 10:27:17,486 [INFO] cluster assigned, event evt-1006 -> cluster de7c545b-b23c-47da-9f15-2f45a386db26 (created_new_cluster)
2026-04-26 10:27:17,487 [INFO] starting to embed the event id evt-1007 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.91it/s]
2026-04-26 10:27:17,658 [INFO] completed to embed the event id evt-1007 using 1 embeddings
2026-04-26 10:27:17,659 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:27:17,659 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:27:17,664 [INFO] in case of approach 1, draft mention if added new event: created draft cluster 59ea6171-f787-49a7-a9c4-baadb673c9dc
2026-04-26 10:27:17,664 [INFO] cluster assigned, event evt-1007 -> cluster 59ea6171-f787-49a7-a9c4-baadb673c9dc (created_new_cluster)
2026-04-26 10:27:17,665 [INFO] starting to embed the event id evt-1008 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  4.97it/s]
2026-04-26 10:27:17,868 [INFO] completed to embed the event id evt-1008 using 1 embeddings
2026-04-26 10:27:17,869 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:27:17,869 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:27:17,875 [INFO] in case of approach 1, draft mention if added new event: created draft cluster c09f098a-f0d7-4b7d-9199-d7c5cf39c27f
2026-04-26 10:27:17,875 [INFO] cluster assigned, event evt-1008 -> cluster c09f098a-f0d7-4b7d-9199-d7c5cf39c27f (created_new_cluster)
2026-04-26 10:27:17,875 [INFO] starting to embed the event id evt-1009 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.46it/s]
2026-04-26 10:27:18,061 [INFO] completed to embed the event id evt-1009 using 1 embeddings
2026-04-26 10:27:18,062 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:27:18,062 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:27:18,067 [INFO] in case of approach 1, draft mention if added new event: created draft cluster 3372c23b-f61b-424c-a52d-84129ee1905b
2026-04-26 10:27:18,067 [INFO] cluster assigned, event evt-1009 -> cluster 3372c23b-f61b-424c-a52d-84129ee1905b (created_new_cluster)
2026-04-26 10:27:18,067 [INFO] starting to embed the event id evt-1010 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.36it/s]
2026-04-26 10:27:18,256 [INFO] completed to embed the event id evt-1010 using 1 embeddings
2026-04-26 10:27:18,257 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:27:18,257 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:27:18,262 [INFO] in case of approach 1, draft mention if added new event: created draft cluster 8cf5af69-c8a9-483b-bd2b-da92ffd2ee14
2026-04-26 10:27:18,262 [INFO] cluster assigned, event evt-1010 -> cluster 8cf5af69-c8a9-483b-bd2b-da92ffd2ee14 (created_new_cluster)
2026-04-26 10:27:18,262 [INFO] starting to embed the event id evt-1011 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.86it/s]
2026-04-26 10:27:18,435 [INFO] completed to embed the event id evt-1011 using 1 embeddings
2026-04-26 10:27:18,436 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:27:18,437 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:27:18,441 [INFO] in case of approach 1, draft mention if added new event: created draft cluster bf44e0a2-3d3b-47e9-bf81-4fc3e52a2bea
2026-04-26 10:27:18,442 [INFO] cluster assigned, event evt-1011 -> cluster bf44e0a2-3d3b-47e9-bf81-4fc3e52a2bea (created_new_cluster)
2026-04-26 10:27:18,442 [INFO] starting to embed the event id evt-1012 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.37it/s]
2026-04-26 10:27:18,630 [INFO] completed to embed the event id evt-1012 using 1 embeddings
2026-04-26 10:27:18,631 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:27:18,631 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:27:18,636 [INFO] in case of approach 1, draft mention if added new event: created draft cluster 9d46358e-861f-46bf-aa37-88976f50dac1
2026-04-26 10:27:18,636 [INFO] cluster assigned, event evt-1012 -> cluster 9d46358e-861f-46bf-aa37-88976f50dac1 (created_new_cluster)
2026-04-26 10:27:18,640 [INFO] transaction committed, all locks released
Running maintenance worker for approach 1...
2026-04-26 10:27:18,652 [INFO] waiting to acquire replay maintenance lock 442001
2026-04-26 10:27:18,653 [INFO] acquired replay maintenance lock 442001 (releases with transaction)
2026-04-26 10:27:18,658 [INFO] maintenance - started scan of 1 draft clusters
2026-04-26 10:27:18,659 [INFO] maintenance - completed scan of draft clusters. Promoted 10 to active.
2026-04-26 10:27:18,659 [INFO] maintenance - transaction committed, replay maintenance lock released
Running approach 2 (Three Gates)...
2026-04-26 10:27:18,669 [INFO] waiting to acquire replay maintenance lock 442001
2026-04-26 10:27:18,670 [INFO] acquired replay maintenance lock 442001 (releases with transaction)
2026-04-26 10:27:18,693 [INFO] waiting to acquire replay maintenance lock 442001
2026-04-26 10:27:18,693 [INFO] acquired replay maintenance lock 442001 (releases with transaction)
2026-04-26 10:27:18,706 [INFO] starting to embed the event id evt-1001 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.89it/s]
2026-04-26 10:27:18,878 [INFO] completed to embed the event id evt-1001 using 1 embeddings
2026-04-26 10:27:18,879 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:27:18,880 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:27:18,881 [INFO] starting rerank for input event id evt-1001, input text: Login errors are spiking in the auth service...
2026-04-26 10:27:18,881 [INFO] completed rerank for input event id evt-1001, result: []
2026-04-26 10:27:18,883 [INFO] llm output - starting
2026-04-26 10:27:18,883 [INFO] llm output - completed, decision: none, confidence: 0.0
2026-04-26 10:27:30,243 [INFO] cluster assigned, event evt-1001 -> cluster cad100a7-8e44-4c2f-815a-39b8ca61e651 (created_new_cluster)
2026-04-26 10:27:30,249 [INFO] starting to embed the event id evt-1002 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  1.45it/s]
2026-04-26 10:27:30,967 [INFO] completed to embed the event id evt-1002 using 1 embeddings
2026-04-26 10:27:30,969 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:27:30,970 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:27:30,971 [INFO] starting rerank for input event id evt-1002, input text: Authentication failures are rising fast for sign i...
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.00it/s]
2026-04-26 10:27:31,175 [INFO] completed rerank for input event id evt-1002, result: [('cad100a7-8e44-4c2f-815a-39b8ca61e651', 0.05796272434767455)]
2026-04-26 10:27:31,176 [INFO] llm output - starting
2026-04-26 10:27:53,260 [INFO] llm output - completed, decision: cluster_a, confidence: 0.85
2026-04-26 10:27:53,337 [INFO] cluster assigned, event evt-1002 -> cluster cad100a7-8e44-4c2f-815a-39b8ca61e651 (joined_existing_cluster)
2026-04-26 10:27:53,339 [INFO] starting to embed the event id evt-1003 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:01<00:00,  1.17s/it]
2026-04-26 10:27:54,532 [INFO] completed to embed the event id evt-1003 using 1 embeddings
2026-04-26 10:27:54,534 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:27:54,534 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:27:54,537 [INFO] starting to embed the event id evt-1004 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  4.70it/s]
2026-04-26 10:27:54,753 [INFO] completed to embed the event id evt-1004 using 1 embeddings
2026-04-26 10:27:54,755 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:27:54,755 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:27:54,756 [INFO] starting rerank for input event id evt-1004, input text: Checkout service is timing out for card payments...
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00, 19.41it/s]
2026-04-26 10:27:54,808 [INFO] completed rerank for input event id evt-1004, result: [('cad100a7-8e44-4c2f-815a-39b8ca61e651', 1.3943291428390853e-05)]
2026-04-26 10:27:54,809 [INFO] llm output - starting
2026-04-26 10:28:11,727 [INFO] llm output - completed, decision: none, confidence: 0.95
2026-04-26 10:28:17,988 [INFO] cluster assigned, event evt-1004 -> cluster f97978c8-d011-49fb-a399-fa816517ba11 (created_new_cluster)
2026-04-26 10:28:17,990 [INFO] starting to embed the event id evt-1005 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:01<00:00,  1.89s/it]
2026-04-26 10:28:19,894 [INFO] completed to embed the event id evt-1005 using 1 embeddings
2026-04-26 10:28:19,898 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:28:19,899 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:28:19,903 [INFO] starting rerank for input event id evt-1005, input text: Card payment flow keeps timing out in checkout...
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00, 12.82it/s]
2026-04-26 10:28:19,982 [INFO] completed rerank for input event id evt-1005, result: [('f97978c8-d011-49fb-a399-fa816517ba11', 0.4546753066940398), ('cad100a7-8e44-4c2f-815a-39b8ca61e651', 1.163785679778121e-05)]
2026-04-26 10:28:19,984 [INFO] llm output - starting
2026-04-26 10:29:07,843 [INFO] llm output - completed, decision: cluster_a, confidence: 0.9
2026-04-26 10:29:07,896 [INFO] cluster assigned, event evt-1005 -> cluster f97978c8-d011-49fb-a399-fa816517ba11 (joined_existing_cluster)
2026-04-26 10:29:07,899 [INFO] starting to embed the event id evt-1006 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:03<00:00,  3.33s/it]
2026-04-26 10:29:11,366 [INFO] completed to embed the event id evt-1006 using 1 embeddings
2026-04-26 10:29:11,376 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:29:11,376 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:29:11,381 [INFO] starting rerank for input event id evt-1006, input text: Weekly sales dashboard needs a brighter chart pale...
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  7.71it/s]
2026-04-26 10:29:11,513 [INFO] completed rerank for input event id evt-1006, result: [('f97978c8-d011-49fb-a399-fa816517ba11', 1.1446181816493591e-05), ('cad100a7-8e44-4c2f-815a-39b8ca61e651', 1.131556112157735e-05)]
2026-04-26 10:29:11,515 [INFO] llm output - starting
2026-04-26 10:29:59,574 [INFO] llm output - completed, decision: none, confidence: 0.95
2026-04-26 10:30:12,153 [INFO] cluster assigned, event evt-1006 -> cluster 9bf8991a-e3cd-4fec-9bf8-915f701a4914 (created_new_cluster)
2026-04-26 10:30:12,157 [INFO] starting to embed the event id evt-1007 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  1.13it/s]
2026-04-26 10:30:13,058 [INFO] completed to embed the event id evt-1007 using 1 embeddings
2026-04-26 10:30:13,061 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:30:13,062 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:30:13,066 [INFO] starting rerank for input event id evt-1007, input text: Users still cannot sign in because auth failures c...
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  9.27it/s]
2026-04-26 10:30:13,175 [INFO] completed rerank for input event id evt-1007, result: [('cad100a7-8e44-4c2f-815a-39b8ca61e651', 2.189325566221487e-05), ('9bf8991a-e3cd-4fec-9bf8-915f701a4914', 1.2414810709006505e-05)]
2026-04-26 10:30:13,176 [INFO] llm output - starting
2026-04-26 10:30:48,024 [INFO] llm output - completed, decision: none, confidence: 0.95
2026-04-26 10:30:58,635 [INFO] cluster assigned, event evt-1007 -> cluster fffb5cc8-a2bd-4b32-87ca-a9e56e4de92a (created_new_cluster)
2026-04-26 10:30:58,746 [INFO] starting to embed the event id evt-1008 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:01<00:00,  1.76s/it]
2026-04-26 10:31:00,619 [INFO] completed to embed the event id evt-1008 using 1 embeddings
2026-04-26 10:31:00,626 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:31:00,627 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:31:00,631 [INFO] starting rerank for input event id evt-1008, input text: Gateway returns 502 during checkout payment reques...
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  6.51it/s]
2026-04-26 10:31:00,787 [INFO] completed rerank for input event id evt-1008, result: [('f97978c8-d011-49fb-a399-fa816517ba11', 0.020671776121795354), ('cad100a7-8e44-4c2f-815a-39b8ca61e651', 1.4767641836562332e-05)]
2026-04-26 10:31:00,789 [INFO] llm output - starting
2026-04-26 10:32:00,263 [INFO] llm output - completed, decision: none, confidence: 0.95
2026-04-26 10:32:08,702 [INFO] cluster assigned, event evt-1008 -> cluster 02d10886-e27c-4c6d-b9a8-7275b10c20cc (created_new_cluster)
2026-04-26 10:32:08,707 [INFO] starting to embed the event id evt-1009 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:01<00:00,  1.23s/it]
2026-04-26 10:32:10,020 [INFO] completed to embed the event id evt-1009 using 1 embeddings
2026-04-26 10:32:10,025 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:32:10,026 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:32:10,030 [INFO] starting rerank for input event id evt-1009, input text: Payment requests fail with 502 errors in checkout ...
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  8.85it/s]
2026-04-26 10:32:10,144 [INFO] completed rerank for input event id evt-1009, result: [('02d10886-e27c-4c6d-b9a8-7275b10c20cc', 0.9995390655566683), ('f97978c8-d011-49fb-a399-fa816517ba11', 0.001962266535985033)]
2026-04-26 10:32:10,146 [INFO] llm output - starting
2026-04-26 10:32:43,229 [INFO] llm output - completed, decision: cluster_a, confidence: 0.9995
2026-04-26 10:32:43,251 [INFO] cluster assigned, event evt-1009 -> cluster 02d10886-e27c-4c6d-b9a8-7275b10c20cc (joined_existing_cluster)
2026-04-26 10:32:43,254 [INFO] starting to embed the event id evt-1010 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:01<00:00,  1.53s/it]
2026-04-26 10:32:44,806 [INFO] completed to embed the event id evt-1010 using 1 embeddings
2026-04-26 10:32:44,812 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:32:44,813 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:32:44,817 [INFO] starting rerank for input event id evt-1010, input text: Password reset links are erroring out for several ...
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00, 18.92it/s]
2026-04-26 10:32:44,872 [INFO] completed rerank for input event id evt-1010, result: [('cad100a7-8e44-4c2f-815a-39b8ca61e651', 0.015464307856299816), ('fffb5cc8-a2bd-4b32-87ca-a9e56e4de92a', 0.002581287170298771)]
2026-04-26 10:32:44,873 [INFO] llm output - starting
2026-04-26 10:33:15,583 [INFO] llm output - completed, decision: both, confidence: 0.95
2026-04-26 10:33:15,646 [INFO] cluster assigned, event evt-1010 -> cluster cad100a7-8e44-4c2f-815a-39b8ca61e651 (joined_existing_cluster)
2026-04-26 10:33:15,654 [INFO] starting to embed the event id evt-1011 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  1.24it/s]
2026-04-26 10:33:16,479 [INFO] completed to embed the event id evt-1011 using 1 embeddings
2026-04-26 10:33:16,482 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:33:16,483 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:33:16,487 [INFO] starting rerank for input event id evt-1011, input text: Users report reset links failing during password r...
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00, 15.78it/s]
2026-04-26 10:33:16,551 [INFO] completed rerank for input event id evt-1011, result: [('cad100a7-8e44-4c2f-815a-39b8ca61e651', 0.000775225898511629), ('02d10886-e27c-4c6d-b9a8-7275b10c20cc', 0.00012534635876626624)]
2026-04-26 10:33:16,553 [INFO] llm output - starting
2026-04-26 10:33:37,551 [INFO] llm output - completed, decision: none, confidence: 0.95
2026-04-26 10:33:46,585 [INFO] cluster assigned, event evt-1011 -> cluster 1e6e6676-614e-4dce-8dd0-5abac4f48b7d (created_new_cluster)
2026-04-26 10:33:46,587 [INFO] starting to embed the event id evt-1012 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  1.39it/s]
2026-04-26 10:33:47,319 [INFO] completed to embed the event id evt-1012 using 1 embeddings
2026-04-26 10:33:47,322 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:33:47,322 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:33:47,328 [INFO] starting rerank for input event id evt-1012, input text: Checkout payment issue still reproduces with gatew...
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  8.67it/s]
2026-04-26 10:33:47,444 [INFO] completed rerank for input event id evt-1012, result: [('02d10886-e27c-4c6d-b9a8-7275b10c20cc', 0.990985877592627), ('f97978c8-d011-49fb-a399-fa816517ba11', 0.0007438687234013553)]
2026-04-26 10:33:47,446 [INFO] llm output - starting
2026-04-26 10:34:15,249 [INFO] llm output - completed, decision: cluster_a, confidence: 0.991
2026-04-26 10:34:15,307 [INFO] cluster assigned, event evt-1012 -> cluster 02d10886-e27c-4c6d-b9a8-7275b10c20cc (joined_existing_cluster)
2026-04-26 10:34:15,469 [INFO] transaction committed, all locks released
Running approach 3 (HDBSCAN)...
2026-04-26 10:34:15,694 [INFO] waiting to acquire replay maintenance lock 442001
2026-04-26 10:34:15,710 [INFO] acquired replay maintenance lock 442001 (releases with transaction)
2026-04-26 10:34:15,901 [INFO] waiting to acquire replay maintenance lock 442001
2026-04-26 10:34:15,902 [INFO] acquired replay maintenance lock 442001 (releases with transaction)
2026-04-26 10:34:15,980 [INFO] starting to embed the event id evt-1001 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  1.57it/s]
2026-04-26 10:34:16,628 [INFO] completed to embed the event id evt-1001 using 1 embeddings
2026-04-26 10:34:16,633 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:34:16,633 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:34:22,882 [INFO] cluster assigned, event evt-1001 -> cluster b33c0722-3531-4912-afef-ce27a616d9e2 (created_new_cluster)
2026-04-26 10:34:22,885 [INFO] starting to embed the event id evt-1002 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  1.32it/s]
2026-04-26 10:34:23,681 [INFO] completed to embed the event id evt-1002 using 1 embeddings
2026-04-26 10:34:23,685 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:34:23,685 [INFO] acquired bucket lock 255 (releases with transaction)
/usr/local/lib/python3.12/site-packages/sklearn/cluster/_hdbscan/hdbscan.py:722: FutureWarning: The default value of `copy` will change from False to True in 1.10. Explicitly set a value for `copy` to silence this warning.
  warn(
2026-04-26 10:34:27,978 [INFO] cluster assigned, event evt-1002 -> cluster 72fa7579-482b-442a-b347-a0b4851b2959 (created_new_cluster)
2026-04-26 10:34:27,979 [INFO] starting to embed the event id evt-1003 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  1.42it/s]
2026-04-26 10:34:28,694 [INFO] completed to embed the event id evt-1003 using 1 embeddings
2026-04-26 10:34:28,697 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:34:28,697 [INFO] acquired bucket lock 255 (releases with transaction)
2026-04-26 10:34:28,703 [INFO] starting to embed the event id evt-1004 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  4.28it/s]
2026-04-26 10:34:28,941 [INFO] completed to embed the event id evt-1004 using 1 embeddings
2026-04-26 10:34:28,945 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:34:28,945 [INFO] acquired bucket lock 255 (releases with transaction)
/usr/local/lib/python3.12/site-packages/sklearn/cluster/_hdbscan/hdbscan.py:722: FutureWarning: The default value of `copy` will change from False to True in 1.10. Explicitly set a value for `copy` to silence this warning.
  warn(
2026-04-26 10:34:33,115 [INFO] cluster assigned, event evt-1004 -> cluster 88bb8dbc-4a65-4dc3-94d6-af46c23a105e (created_new_cluster)
2026-04-26 10:34:33,118 [INFO] starting to embed the event id evt-1005 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  2.50it/s]
2026-04-26 10:34:33,544 [INFO] completed to embed the event id evt-1005 using 1 embeddings
2026-04-26 10:34:33,547 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:34:33,547 [INFO] acquired bucket lock 255 (releases with transaction)
/usr/local/lib/python3.12/site-packages/sklearn/cluster/_hdbscan/hdbscan.py:722: FutureWarning: The default value of `copy` will change from False to True in 1.10. Explicitly set a value for `copy` to silence this warning.
  warn(
2026-04-26 10:34:33,572 [INFO] cluster assigned, event evt-1005 -> cluster 72fa7579-482b-442a-b347-a0b4851b2959 (joined_existing_cluster)
2026-04-26 10:34:33,572 [INFO] starting to embed the event id evt-1006 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  4.30it/s]
2026-04-26 10:34:33,810 [INFO] completed to embed the event id evt-1006 using 1 embeddings
2026-04-26 10:34:33,814 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:34:33,815 [INFO] acquired bucket lock 255 (releases with transaction)
/usr/local/lib/python3.12/site-packages/sklearn/cluster/_hdbscan/hdbscan.py:722: FutureWarning: The default value of `copy` will change from False to True in 1.10. Explicitly set a value for `copy` to silence this warning.
  warn(
2026-04-26 10:34:41,370 [INFO] cluster assigned, event evt-1006 -> cluster 7b9d3583-f588-41b6-9943-ead2c6968cdd (created_new_cluster)
2026-04-26 10:34:41,372 [INFO] starting to embed the event id evt-1007 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:01<00:00,  1.99s/it]
2026-04-26 10:34:43,367 [INFO] completed to embed the event id evt-1007 using 1 embeddings
2026-04-26 10:34:43,375 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:34:43,376 [INFO] acquired bucket lock 255 (releases with transaction)
/usr/local/lib/python3.12/site-packages/sklearn/cluster/_hdbscan/hdbscan.py:722: FutureWarning: The default value of `copy` will change from False to True in 1.10. Explicitly set a value for `copy` to silence this warning.
  warn(
2026-04-26 10:34:43,394 [INFO] cluster assigned, event evt-1007 -> cluster 72fa7579-482b-442a-b347-a0b4851b2959 (joined_existing_cluster)
2026-04-26 10:34:43,395 [INFO] starting to embed the event id evt-1008 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.47it/s]
2026-04-26 10:34:43,583 [INFO] completed to embed the event id evt-1008 using 1 embeddings
2026-04-26 10:34:43,585 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:34:43,586 [INFO] acquired bucket lock 255 (releases with transaction)
/usr/local/lib/python3.12/site-packages/sklearn/cluster/_hdbscan/hdbscan.py:722: FutureWarning: The default value of `copy` will change from False to True in 1.10. Explicitly set a value for `copy` to silence this warning.
  warn(
2026-04-26 10:34:43,596 [INFO] cluster assigned, event evt-1008 -> cluster 88bb8dbc-4a65-4dc3-94d6-af46c23a105e (joined_existing_cluster)
2026-04-26 10:34:43,597 [INFO] starting to embed the event id evt-1009 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.25it/s]
2026-04-26 10:34:43,792 [INFO] completed to embed the event id evt-1009 using 1 embeddings
2026-04-26 10:34:43,794 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:34:43,794 [INFO] acquired bucket lock 255 (releases with transaction)
/usr/local/lib/python3.12/site-packages/sklearn/cluster/_hdbscan/hdbscan.py:722: FutureWarning: The default value of `copy` will change from False to True in 1.10. Explicitly set a value for `copy` to silence this warning.
  warn(
2026-04-26 10:34:43,804 [INFO] cluster assigned, event evt-1009 -> cluster 88bb8dbc-4a65-4dc3-94d6-af46c23a105e (joined_existing_cluster)
2026-04-26 10:34:43,805 [INFO] starting to embed the event id evt-1010 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  6.03it/s]
2026-04-26 10:34:43,976 [INFO] completed to embed the event id evt-1010 using 1 embeddings
2026-04-26 10:34:43,979 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:34:43,979 [INFO] acquired bucket lock 255 (releases with transaction)
/usr/local/lib/python3.12/site-packages/sklearn/cluster/_hdbscan/hdbscan.py:722: FutureWarning: The default value of `copy` will change from False to True in 1.10. Explicitly set a value for `copy` to silence this warning.
  warn(
2026-04-26 10:34:48,166 [INFO] cluster assigned, event evt-1010 -> cluster 04b58837-17b9-4eb3-84c8-3598faecd0a9 (created_new_cluster)
2026-04-26 10:34:48,167 [INFO] starting to embed the event id evt-1011 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  1.39it/s]
2026-04-26 10:34:48,897 [INFO] completed to embed the event id evt-1011 using 1 embeddings
2026-04-26 10:34:48,900 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:34:48,900 [INFO] acquired bucket lock 255 (releases with transaction)
/usr/local/lib/python3.12/site-packages/sklearn/cluster/_hdbscan/hdbscan.py:722: FutureWarning: The default value of `copy` will change from False to True in 1.10. Explicitly set a value for `copy` to silence this warning.
  warn(
2026-04-26 10:34:48,914 [INFO] cluster assigned, event evt-1011 -> cluster 04b58837-17b9-4eb3-84c8-3598faecd0a9 (joined_existing_cluster)
2026-04-26 10:34:48,915 [INFO] starting to embed the event id evt-1012 using 1 embeddings
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  4.40it/s]
2026-04-26 10:34:49,147 [INFO] completed to embed the event id evt-1012 using 1 embeddings
2026-04-26 10:34:49,149 [INFO] waiting to acquire bucket lock 255
2026-04-26 10:34:49,150 [INFO] acquired bucket lock 255 (releases with transaction)
/usr/local/lib/python3.12/site-packages/sklearn/cluster/_hdbscan/hdbscan.py:722: FutureWarning: The default value of `copy` will change from False to True in 1.10. Explicitly set a value for `copy` to silence this warning.
  warn(
2026-04-26 10:34:49,165 [INFO] cluster assigned, event evt-1012 -> cluster 88bb8dbc-4a65-4dc3-94d6-af46c23a105e (joined_existing_cluster)
2026-04-26 10:34:49,176 [INFO] transaction committed, all locks released
             Clustering Evaluation Results             
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┓
┃ Approach            ┃ Precision ┃ Recall ┃ F1 Score ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━┩
│ 1 - Score Partition │    1.0000 │ 0.0588 │   0.1111 │
│ 2 - Three Gates     │    0.7143 │ 0.5882 │   0.6452 │
│ 3 - HDBSCAN         │    0.8182 │ 0.5294 │   0.6429 │
└─────────────────────┴───────────┴────────┴──────────┘
Saved results to /app/./scripts/reports/evaluation_results.json
```

```bash
docker compose exec api python ./scripts/evaluate_hybrid.py ./data/baseline_story.jsonl
```
#### output
```bash
root@7a9c7617f233:/app#  python ./scripts/evaluate_hybrid.py ./data/baseline_story.jsonl
2026-04-26 11:39:31,922 [INFO] waiting to acquire replay maintenance lock 442001
2026-04-26 11:39:31,922 [INFO] acquired replay maintenance lock 442001 (releases with transaction)
2026-04-26 11:39:31,941 [INFO] waiting to acquire replay maintenance lock 442001
2026-04-26 11:39:31,942 [INFO] acquired replay maintenance lock 442001 (releases with transaction)
2026-04-26 11:39:31,957 [INFO] transaction committed, all locks released
2026-04-26 11:39:31,957 [INFO] Loading Embedder, Reranker, and Judge...
2026-04-26 11:39:35,311 [INFO] Use pytorch device_name: cpu
2026-04-26 11:39:35,311 [INFO] Load pretrained SentenceTransformer: codefuse-ai/F2LLM-v2-0.6B
2026-04-26 11:39:44,837 [INFO] 2 prompts are loaded, with the keys: ['query', 'document']
2026-04-26 11:39:46,737 [INFO] Use pytorch device: cpu
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  4.28it/s]
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.98it/s]
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.95it/s]
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  6.04it/s]
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  6.01it/s]
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  6.12it/s]
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  6.08it/s]
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.43it/s]
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.22it/s]
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.57it/s]
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  6.09it/s]
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.28it/s]
2026-04-26 11:39:49,004 [INFO] Running HDBSCAN...
/usr/local/lib/python3.12/site-packages/sklearn/cluster/_hdbscan/hdbscan.py:722: FutureWarning: The default value of `copy` will change from False to True in 1.10. Explicitly set a value for `copy` to silence this warning.
  warn(
2026-04-26 11:40:03,315 [INFO] Formed 6 initial clusters.
2026-04-26 11:40:03,315 [INFO] --- Strict Merge Iteration 1 ---
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  6.29it/s]
2026-04-26 11:40:22,223 [INFO] Top-1 Match: cluster_3 -> cluster_1 | LLM Decision: separate (0.95)
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00, 12.42it/s]
2026-04-26 11:40:34,003 [INFO] Top-1 Match: cluster_4 -> cluster_0 | LLM Decision: separate (0.95)
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  2.84it/s]
2026-04-26 11:40:45,151 [INFO] Top-1 Match: cluster_2 -> cluster_1 | LLM Decision: merge (0.95)
2026-04-26 11:40:45,151 [INFO] *** Verified Merge: cluster_2 into cluster_1 ***
2026-04-26 11:40:56,590 [INFO] --- Strict Merge Iteration 2 ---
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  1.10it/s]
2026-04-26 11:42:54,080 [INFO] Top-1 Match: cluster_3 -> cluster_4 | LLM Decision: merge (0.95)
2026-04-26 11:42:54,081 [INFO] *** Verified Merge: cluster_3 into cluster_4 ***
2026-04-26 11:43:02,981 [INFO] --- Strict Merge Iteration 3 ---
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  2.47it/s]
2026-04-26 11:43:40,501 [INFO] Top-1 Match: cluster_4 -> cluster_0 | LLM Decision: separate (0.95)
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  3.29it/s]
2026-04-26 11:44:11,217 [INFO] Top-1 Match: noise_0 -> cluster_4 | LLM Decision: separate (0.95)
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  4.71it/s]
2026-04-26 11:44:41,718 [INFO] Top-1 Match: cluster_1 -> cluster_4 | LLM Decision: separate (0.95)
Batches: 100%|███████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  2.65it/s]
2026-04-26 11:45:05,968 [INFO] Top-1 Match: cluster_0 -> cluster_4 | LLM Decision: separate (0.85)
        Strict Top-1 Hybrid Evaluation Results        
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┓
┃ Approach           ┃ Precision ┃ Recall ┃ F1 Score ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━┩
│ Strict HDBSCAN+LLM │    1.0000 │ 1.0000 │   1.0000 │
└────────────────────┴───────────┴────────┴──────────┘
root@7a9c7617f233:/app# exit
exit
```



## API
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Event stream: `GET /events/stream`

## Model Cache
- Location: `./.cache/`
- Purpose: stores the configured sentence-transformers model and manifest metadata for the primary semantic vector path
- Git behavior: `.cache/` is ignored in `.gitignore`
- Reset behavior: `demo reset` does not touch `.cache/`

In the packaged Docker demo, the default `embedding_backend` is `sentence-transformers`, so the first run warms the local cache by downloading the configured model into `.cache/models/sentence-transformers`. Manifest metadata stays alongside that cache under `.cache/models`. The system also maintains a deterministic stable-projection vector for every event and cluster.

Projection and semantic vectors are stored separately:
- projection vectors are always written to `projection_embeddings`
- semantic vectors are written to `semantic_embeddings` only when the model is available
- if the semantic model is unavailable, the system does **not** copy projection vectors into semantic storage
- the `MaintenanceWorker` backfills missing semantic event and cluster vectors later when semantic embedding becomes available again
- a shared `semantic_ready_for_active_window` flag keeps online retrieval on projection until missing semantic rows in the active horizon reach zero

If the transformer backend is unavailable, or if `vector_mode` is forced to `stable_projection`, clustering pivots to that sparse bag-of-words projection instead of a cryptographic hash.

## Algorithm Approaches Implemented
The following pseudocode outlines the progression from basic heuristic filtering to advanced hybrid semantic clustering for incident deduplication.

### Approach 1: Heuristic Attribute Filtering

This approach applies logical filters to exclude noise and uses a recency-adjusted scoring mechanism to determine cluster membership. By combining categorical exclusion with exponential decay, the system maintains a high-quality event stream while allowing for temporal fluidity.

#### 1. Global Sanitation Logic
The filter evaluates two primary criteria to ensure only high-signal data triggers state changes:
1.  **Categorical Exclusion**: Discards events labeled as `character introduction` (initialization noise).
2.  **Quality Floor**: Retains events only if they meet a minimum `score` (0.5) to prevent low-confidence logs from polluting clusters.

```python
# Pseudocode: Global Sanitation
For each event in input_stream:
    # Remove low-confidence signals
    if event.quality_score < 0.5:
        Discard event
    Else:
        Append to filtered_stream
```

#### 2. Scoring Math: Recency-Adjusted Similarity
The system determines cluster membership using a formula that decays similarity over time, avoiding hard temporal cliffs.

**Core Formula:**
$$S_{final} = S_{semantic} \times e^{(-\lambda \times \Delta t)}$$

* **$S_{semantic}$**: Embedding-based similarity (Vector Cosine Similarity).
* **$\Delta t$**: Cluster age gap in minutes (since `last_seen_at`).
* **$\lambda$**: Decay constant, derived from a configurable half-life: $\lambda = \ln(2) / \text{half\_life\_minutes}$.

#### 3. Implementation: State Rehydration
The `reset_with_events` method synchronizes mappings and calculates the operational baseline.

```python
def reset_with_events(self, events, rehydrate_runtime=True):
    # Synchronize internal counters and mappings
    self.event_id_counter = max([e.event_id for e in events]) + 1
    self.event_id_to_cluster_id = {e.event_id: e.cluster_id for e in events}
    
    # Calculate Final Score using Exponential Decay
    for event in events:
        time_weight = math.exp(-self.lambda_val * event.delta_t)
        event.final_score = event.semantic_similarity * time_weight
        
    # Rebuild cluster membership
    self.cluster_id_to_event_ids = {
        c_id: set([e.event_id for e in events if e.cluster_id == c_id]) 
        for c_id in set(self.event_id_to_cluster_id.values())
    }
    
    # Recalculate global operational baseline
    self.baseline = sum(e.baseline for e in events) / len(events)
    return self
```

### 4. Deterministic Fallbacks & Maintenance
To ensure system resilience, the scoring math adapts to the available infrastructure:
* **Degraded Mode**: If the semantic model is offline, the formula applies to **Projection Embeddings** (sparse bag-of-words projections) instead of semantic vectors.
* **Storage Integrity**: `projection_embeddings` and `semantic_embeddings` are stored in separate tables. This ensures the semantic table is never "polluted" by fallback data.
* **Maintenance Worker**: An asynchronous process backfills missing semantic rows when the model returns and merges "Draft" clusters if the combined evidence eventually clears the `merge_evidence_threshold`.
---

### Approach 2: Multi-Stage Sequential Gating
**Goal:** Identify relationships using bi-encoder, reranker and llm-as judge.

```python
# Phase 1: Semantic Clustering
Cluster_Vectors = Generate_Semantic_Vectors(Events)
Event_Vector = Generate_Semantic_Vectors(Event)

# Phase 2: Sequential Gating
For each Event:
    Semantic_Cluster = Vector_Cosine_Similarity(Event_Vector, Cluster_Vectors, top-30)
    Reranker_Cluster = Vector_Cosine_Similarity(Event, Semantic_Cluster, top-2)
    If LLM_As_Judge(Reranker_Cluster, Event)==Merge_ALL: 
        Assign_Event_to_Cluster(Event, Reranker_Cluster)
        
    elif LLM_As_Judge(Reranker_Cluster, Event)==Rerank_Cluster_First:
        Assign_Event_to_Cluster(Event, Reranker_Cluster_First)
        Exit Loop
    elif LLM_As_Judge(Reranker_Cluster, Event)==Rerank_Cluster_Second:
        Assign_Event_to_Cluster(Event, Reranker_Cluster_Second)
    else:
        Assign_Event_to_Cluster(Event)
    Exit Loop

```

---

### Approach 3: Density-Based Clustering (HDBSCAN)
**Goal:** Discover clusters of varying shapes and densities without pre-defining the number of incidents.

```python
# Feature Engineering
Matrix = Extract_Features(Events)

# Density Analysis
# min_cluster_size: Minimum events to form an incident
# min_samples: Controls how conservative the clustering is
Model = HDBSCAN(min_cluster_size=2, min_samples=1)
Labels = Model.fit_predict(Matrix)

# Mapping & Noise Handling
For i, label in Labels:
    If label == -1:
        Assign_To_Cluster(Events[i])
    Else:
        Assign_To_Cluster(Events[i])
```

---

### Approach 4: Hybrid Semantic Refinement (HDBSCAN + LLM)
**Goal:** Combine statistical grouping with LLM-driven "SRE intuition" to resolve evolving incidents.

```python
# Phase 1: Statistical Baseline
Embeddings = Generate_Semantic_Vectors(Events)
Initial_Clusters = HDBSCAN(Embeddings)

# Phase 2: Iterative Semantic Consolidation
For each Target_Cluster:
    # Find the most semantically similar neighbor via Reranker
    Candidate = Reranker.find_nearest(Target_Cluster, All_Clusters)
    
    # LLM Verification (The Logic Gate)
    Decision = LLM_Judge.evaluate(
        Context_A = Target_Cluster.summary,
        Context_B = Candidate.summary,
        Criteria = "Simillar text"
    )
    
    # High-confidence Merge
    If Decision.action == "merge":
        Combine(Target_Cluster, Candidate)
        Regenerate_Consolidated_Summary(Target_Cluster)
```

## Extra commands for debugging

In shell:

```bash
docker compose exec api demo watch
docker compose exec api demo replay --rebase-now
```

`demo watch` renders the live stream, active cluster state, and recent merges side by side.

Restore the live baseline story without removing Docker volumes:

```bash
docker compose exec api demo reset
```

Calibrate thresholds from the labeled story:

```bash
docker compose exec api demo calibrate
```

Replay the larger week-long sample in a fresh demo window:

```bash
docker compose exec api demo replay --story-path data/week_story_1000.jsonl --rebase-now
docker compose exec api demo calibrate --story-path data/week_story_1000.jsonl --labels-path data/week_story_1000.labels.json
```

## Important Paths
- Demo config: [config/demo.yaml](config/demo.yaml)
- Baseline story: [data/baseline_story.jsonl](data/baseline_story.jsonl)
- Story labels: [data/baseline_story.labels.json](data/baseline_story.labels.json)
- Week-long sample: [data/week_story_1000.jsonl](data/week_story_1000.jsonl)
- Week-long sample labels: [data/week_story_1000.labels.json](data/week_story_1000.labels.json)
- Spec pack: [specs/recent-event-clustering-demo](specs/recent-event-clustering-demo)
- Runbook: [docs/demo-runbook.md](docs/demo-runbook.md)

## Technical Deep Dives
- Scoring math: [docs/scoring-math.md](docs/scoring-math.md)
- Calibration workflow: [docs/calibration-playbook.md](docs/calibration-playbook.md)
- Interview presentation guide: [docs/interview-walkthrough.md](docs/interview-walkthrough.md)
- Architecture design: [specs/recent-event-clustering-demo/design.md](specs/recent-event-clustering-demo/design.md)
- Core clustering service: [src/demo/services/clustering_service.py](src/demo/services/clustering_service.py)
- Reset behavior: [src/demo/services/reset_service.py](src/demo/services/reset_service.py)
