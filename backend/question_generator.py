import re
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from database import Job, Candidate

logger = logging.getLogger(__name__)


class GeneratedQuestion(BaseModel):
    category: str = Field("technical", description="technical, behavioural, or situational")
    difficulty: str = Field("Intermediate", description="Beginner, Intermediate, or Advanced")
    question_text: str = Field(description="The interview question text")
    target_skill: str = Field("", description="Primary skill or competency assessed")
    sample_ideal_answer: str = Field("", description="Key elements of an ideal answer")
    follow_up_question: str = Field("", description="Deeper probing follow-up question")
    evaluation_criteria: str = Field("", description="What the interviewer should look for")


class InterviewQuestionSet(BaseModel):
    job_title: str
    candidate_name: str
    technical_questions: List[GeneratedQuestion] = Field(default_factory=list)
    behavioural_questions: List[GeneratedQuestion] = Field(default_factory=list)
    situational_questions: List[GeneratedQuestion] = Field(default_factory=list)


# --- Deterministic Offline Question Bank ---

TECH_QUESTION_BANK: Dict[str, Dict[str, List[Dict[str, str]]]] = {
    "python": {
        "Beginner": [
            {
                "question": "Explain the difference between a list and a tuple in Python, and when you would prefer one over the other.",
                "target_skill": "python",
                "ideal_answer": "Lists are mutable, dynamic arrays; tuples are immutable, fixed-size. Tuples are memory-efficient, hashable (can be dict keys), and enforce data integrity.",
                "follow_up": "How does Python handle memory allocation differently for lists versus tuples?",
                "criteria": "Understanding of mutability, memory overhead, hashability, and common use cases.",
            },
            {
                "question": "How do Python generators work, and what is the difference between 'yield' and 'return'?",
                "target_skill": "python",
                "ideal_answer": "'yield' pauses function execution and produces values lazily one at a time via the iterator protocol, preserving state. 'return' terminates and sends the whole value.",
                "follow_up": "How would you create an infinite sequence generator without causing an Out-Of-Memory error?",
                "criteria": "Clarity on lazy evaluation, memory efficiency, and generator objects.",
            },
        ],
        "Intermediate": [
            {
                "question": "What is Python's Global Interpreter Lock (GIL), and how do you achieve true parallelism for CPU-bound tasks?",
                "target_skill": "python",
                "ideal_answer": "The GIL is a mutex preventing multiple native threads from executing Python bytecodes simultaneously. For CPU-bound tasks, use multiprocessing, C-extensions, or subinterpreters (PEP 684/703).",
                "follow_up": "When would threading still be beneficial over multiprocessing in Python?",
                "criteria": "Deep understanding of concurrency, CPU vs I/O bound bottlenecks, and multiprocessing vs threading.",
            },
            {
                "question": "How do Python decorators work under the hood, and how do you preserve function metadata using functools.wraps?",
                "target_skill": "python",
                "ideal_answer": "Decorators are higher-order functions that take a function as an argument and return a modified wrapper. functools.wraps copies __name__, __doc__, and annotations to the wrapper.",
                "follow_up": "How would you implement a decorator that accepts custom configuration arguments (e.g. @rate_limit(max_per_min=60))?",
                "criteria": "Closure mechanisms, decorator factory patterns, and metadata preservation.",
            },
        ],
        "Advanced": [
            {
                "question": "Explain Python's memory management: reference counting, cyclic garbage collection (generational gc), and the small object allocator (PyMalloc).",
                "target_skill": "python",
                "ideal_answer": "Reference counting handles immediate deallocation. The cyclic GC uses three generations (Gen 0, 1, 2) with doubly linked lists to detect unreachable reference cycles. PyMalloc manages pools/arenas for allocations <= 512 bytes.",
                "follow_up": "How would you diagnose and resolve a severe memory leak caused by cyclic references in a high-throughput microservice?",
                "criteria": "Internal CPython architecture knowledge, gc module tuning, and memory profiling.",
            },
        ],
    },
    "pytorch": {
        "Beginner": [
            {
                "question": "What is a PyTorch Tensor, and how does it differ from a standard NumPy ndarray?",
                "target_skill": "pytorch",
                "ideal_answer": "PyTorch tensors support GPU acceleration (CUDA) and automatic differentiation (Autograd), whereas NumPy arrays only execute on the CPU without native gradient graphs.",
                "follow_up": "How do you move tensors between CPU and GPU devices cleanly in PyTorch?",
                "criteria": "CUDA device allocation, memory copying, and tensor properties.",
            }
        ],
        "Intermediate": [
            {
                "question": "Explain PyTorch Autograd: dynamic computational graphs, requires_grad, and torch.no_grad() during inference.",
                "target_skill": "pytorch",
                "ideal_answer": "PyTorch builds tape-based dynamic computation graphs at runtime. `requires_grad=True` records operations for `.backward()`. `torch.no_grad()` disables gradient tracking, saving substantial GPU VRAM.",
                "follow_up": "What happens if you forget to call `optimizer.zero_grad()` before the backward pass?",
                "criteria": "Gradient accumulation mechanics, backpropagation, and memory optimization.",
            }
        ],
        "Advanced": [
            {
                "question": "How do DistributedDataParallel (DDP) and Fully Sharded Data Parallel (FSDP) optimize training throughput across multi-node GPU clusters?",
                "target_skill": "pytorch",
                "ideal_answer": "DDP replicates the model across GPUs and overlaps backward pass computation with AllReduce gradient communication. FSDP shards model parameters, gradients, and optimizer states across ranks to train models exceeding single GPU VRAM.",
                "follow_up": "How would you handle tensor parallelism vs pipeline parallelism for a 70B parameter LLM?",
                "criteria": "Deep distributed training architecture, communication overhead reduction, and sharding strategies.",
            }
        ],
    },
    "sql": {
        "Beginner": [
            {
                "question": "What is the difference between WHERE and HAVING clauses in SQL?",
                "target_skill": "sql",
                "ideal_answer": "WHERE filters rows before aggregation (GROUP BY); HAVING filters groups after aggregate functions (e.g. SUM, COUNT) have been calculated.",
                "follow_up": "Can you use aggregate functions directly in a WHERE clause? Why or why not?",
                "criteria": "SQL query execution order (FROM -> WHERE -> GROUP BY -> HAVING -> SELECT -> ORDER BY).",
            }
        ],
        "Intermediate": [
            {
                "question": "Explain SQL Window Functions (e.g., ROW_NUMBER, RANK, DENSE_RANK, LEAD, LAG) and how the OVER(PARTITION BY ...) clause works.",
                "target_skill": "sql",
                "ideal_answer": "Window functions perform calculations across a subset of table rows related to the current row without collapsing rows like GROUP BY. PARTITION BY divides into partitions, and ORDER BY defines calculation order.",
                "follow_up": "How would you find the top 3 highest-earning employees in each department using window functions?",
                "criteria": "Proficiency with complex analytics queries and window partitioning.",
            }
        ],
        "Advanced": [
            {
                "question": "How do B-Tree and Hash indexes work in relational engines? Explain query execution plan analysis (EXPLAIN ANALYZE) and resolving index scans vs sequential scans.",
                "target_skill": "sql",
                "ideal_answer": "B-Tree indexes maintain sorted tree structures ideal for range scans and equality. Hash indexes only support O(1) equality. EXPLAIN ANALYZE reveals actual execution time, node types, buffer hits, and sequential table scans.",
                "follow_up": "What is a covering index and how does index-only scan eliminate heap lookups?",
                "criteria": "Database indexing internals, query planner cost models, and performance tuning.",
            }
        ],
    },
    "docker": {
        "Beginner": [
            {
                "question": "What is the difference between a Docker Image and a Docker Container?",
                "target_skill": "docker",
                "ideal_answer": "A Docker Image is an immutable, read-only template with instructions; a Container is a runnable, isolated instance of an image with a read-write layer.",
                "follow_up": "What is the purpose of the CMD vs ENTRYPOINT instruction in a Dockerfile?",
                "criteria": "Core virtualization understanding, container lifecycle, and Dockerfile fundamentals.",
            }
        ],
        "Intermediate": [
            {
                "question": "How do Docker multi-stage builds work and why are they critical for production microservices?",
                "target_skill": "docker",
                "ideal_answer": "Multi-stage builds allow using intermediate build environments to compile binaries/assets, then copying only final artifacts into a lean minimal runtime image (e.g. alpine or distroless), slashing image size and attack surface.",
                "follow_up": "How would you optimize layer caching in Docker when requirements.txt or package.json changes infrequently?",
                "criteria": "Container security, layer caching optimization, and image footprint reduction.",
            }
        ],
        "Advanced": [
            {
                "question": "How do Linux namespaces, cgroups, and overlay2 storage drivers provide container isolation at the kernel level?",
                "target_skill": "docker",
                "ideal_answer": "Namespaces isolate process trees (pid), networking (net), mounts (mnt), and user IDs. Cgroups limit and monitor hardware resources (CPU, RAM, I/O). Overlay2 merges LowerDir and UpperDir copy-on-write filesystem layers.",
                "follow_up": "How would you troubleshoot an out-of-memory killed (OOMKilled) container in a Kubernetes pod?",
                "criteria": "Linux kernel internals, cgroup memory enforcement, and container observability.",
            }
        ],
    },
    "react": {
        "Beginner": [
            {
                "question": "What is the virtual DOM in React, and how does reconciliation work?",
                "target_skill": "react",
                "ideal_answer": "The virtual DOM is an in-memory representation of UI elements. React compares the previous and new virtual DOM tree (diffing algorithm) and updates only changed nodes in the real browser DOM.",
                "follow_up": "Why is the 'key' prop important when rendering dynamic lists in React?",
                "criteria": "Rendering lifecycle, reconciliation, and component re-render performance.",
            }
        ],
        "Intermediate": [
            {
                "question": "Explain the rules of React Hooks and compare useMemo, useCallback, and React.memo.",
                "target_skill": "react",
                "ideal_answer": "useMemo caches calculated values; useCallback caches function definitions across renders; React.memo prevents re-renders when parent props have not changed shallowly.",
                "follow_up": "What can cause an infinite re-render loop inside a useEffect hook?",
                "criteria": "Hook dependency arrays, referential equality, and render optimization.",
            }
        ],
        "Advanced": [
            {
                "question": "How do React 18+ Concurrent Features (Transitions, Suspense, Server Components) work under the Fiber architecture?",
                "target_skill": "react",
                "ideal_answer": "Fiber breaks rendering work into interruptible incremental units with priority queues. Transitions mark non-urgent state updates, keeping the UI responsive. React Server Components render on the backend with zero client bundle impact.",
                "follow_up": "How would you architect a high-traffic micro-frontend application with shared state and code splitting?",
                "criteria": "Modern React architecture, concurrent scheduling, and streaming SSR.",
            }
        ],
    },
    "fastapi": {
        "Beginner": [
            {
                "question": "What makes FastAPI different from Flask or Django?",
                "target_skill": "fastapi",
                "ideal_answer": "FastAPI is built on Starlette and Pydantic with native async/await support, automatic OpenAPI/Swagger documentation generation, and high-performance type validation.",
                "follow_up": "How does Pydantic validate request payloads in a FastAPI route?",
                "criteria": "Understanding of asynchronous I/O, type hinting, and API documentation.",
            }
        ],
        "Intermediate": [
            {
                "question": "How does FastAPI's Dependency Injection system (`Depends`) work and how do you implement database session management?",
                "target_skill": "fastapi",
                "ideal_answer": "`Depends` allows modular sharing of logic, authentication, and database sessions. Using Python context generators (`yield db`), FastAPI handles cleanup automatically after request completion.",
                "follow_up": "How would you implement role-based access control (RBAC) middleware using FastAPI dependencies?",
                "criteria": "Dependency injection patterns, session lifecycles, and security middleware.",
            }
        ],
        "Advanced": [
            {
                "question": "How do you optimize a FastAPI service handling 10,000 requests/sec with asynchronous database pools (asyncpg), background tasks, and connection pooling?",
                "target_skill": "fastapi",
                "ideal_answer": "Use uvloop with gunicorn/uvicorn workers, asyncpg non-blocking connection pools, Redis caching layers, and offload CPU-heavy or I/O tasks to Celery/Kafka message brokers.",
                "follow_up": "What happens when blocking CPU code is called inside an `async def` route in FastAPI?",
                "criteria": "Async event loop concurrency, event loop starvation prevention, and high-load scalability.",
            }
        ],
    },
}

BEHAVIOURAL_QUESTIONS = [
    {
        "question": "Describe a challenging technical project you delivered under tight deadlines. How did you prioritize requirements and manage technical debt?",
        "target_skill": "Agile Prioritization & Ownership",
        "ideal_answer": "Candidate uses STAR format (Situation, Task, Action, Result). Demonstrates trade-off analysis, MVP scope definition, communication with stakeholders, and proactive debt remediation.",
        "follow_up": "Looking back, what architectural or workflow decision would you make differently?",
        "criteria": "Problem-solving maturity, stakeholder alignment, and ownership mindset.",
    },
    {
        "question": "Tell me about a time you had a strong technical disagreement with a teammate or lead. How did you navigate the conflict and reach consensus?",
        "target_skill": "Collaboration & Conflict Resolution",
        "ideal_answer": "Candidate focuses on data-driven benchmarks, architectural trade-offs, empathetic listening, and team alignment rather than personal preference.",
        "follow_up": "If the team chose an approach you still disagreed with, how did you ensure successful execution?",
        "criteria": "Disagree-and-commit mindset, emotional intelligence, and technical collaboration.",
    },
    {
        "question": "Can you share an experience where a critical bug or production incident occurred on a system you maintained? What was your debugging approach and post-mortem strategy?",
        "target_skill": "Incident Response & Reliability",
        "ideal_answer": "Highlights calm triage, log/metric analysis, mitigating customer impact first, followed by root-cause analysis (5 Whys) and automated regression tests in CI/CD.",
        "follow_up": "How did you ensure the same class of bug could never happen again?",
        "criteria": "System resilience thinking, blameless post-mortem culture, and observability.",
    },
]

SITUATIONAL_QUESTIONS = [
    {
        "question": "You are asked to architect a new microservice that needs to handle sudden 10x traffic spikes with sub-50ms latency. How would you design the architecture and choose your tech stack?",
        "target_skill": "System Design & Scalability",
        "ideal_answer": "Proposes horizontal auto-scaling, asynchronous queueing (Kafka/RabbitMQ), distributed caching (Redis), database read-replicas, and CDN edge caching.",
        "follow_up": "How would you prevent cache stampede or thundering herd problems during sudden cache invalidation?",
        "criteria": "Distributed architecture principles, bottleneck identification, and fault tolerance.",
    },
    {
        "question": "If our automated CI/CD pipeline starts failing intermittently due to flaky integration tests, how would you systematically diagnose and resolve the issue?",
        "target_skill": "CI/CD & DevOps Engineering",
        "ideal_answer": "Isolates test environment dependencies, checks for shared state/database race conditions, introduces hermetic mock containers, and establishes flakiness tracking metrics.",
        "follow_up": "How do you balance thorough end-to-end testing with rapid build times?",
        "criteria": "Testing pyramid, deterministic builds, and developer experience.",
    },
]


# ==============================================================================
# QUESTION GENERATION ENGINE (LLM + OFFLINE HEURISTIC)
# ==============================================================================

def generate_interview_questions(
    job: Job,
    candidate: Optional[Candidate] = None,
    provider: str = "google",
    api_key: Optional[str] = None,
    count_per_category: int = 3,
) -> InterviewQuestionSet:
    """
    Generates a structured, role-specific set of technical, behavioural, and situational interview questions.
    Categorized into Beginner, Intermediate, and Advanced tiers.
    """
    cand_name = candidate.full_name if candidate else "Candidate"
    cand_skills = candidate.skills if candidate else []
    job_skills = job.required_skills or []
    job_title = job.title

    # Target key skills (intersection of candidate skills and job requirements, plus remaining job requirements)
    matched_skills = [s for s in cand_skills if s in job_skills]
    focus_skills = matched_skills if matched_skills else job_skills
    if not focus_skills:
        focus_skills = ["python", "sql", "git"]

    # 1. Attempt LLM generation if API Key is configured
    if api_key:
        try:
            cand_context = f"Candidate Name: {cand_name}\nCandidate Skills: {', '.join(cand_skills)}\nCandidate Experience: {candidate.parsed_experience if candidate else 0} years\nProjects: {', '.join(candidate.projects if candidate else [])}"
            job_context = f"Job Title: {job.title}\nRole: {job.role}\nRequired Skills: {', '.join(job_skills)}\nExperience Required: {job.min_experience} years\nJob Description: {job.description[:400]}"

            prompt = f"""
You are an expert technical interviewer and hiring director.
Generate a comprehensive interview question set for this candidate applying for the job.

{job_context}

{cand_context}

Requirements:
1. Technical Questions:
   - Provide technical questions categorized across difficulties: Beginner, Intermediate, and Advanced.
   - Tailor them directly to the candidate's skills and the job's required technologies.
   - Include specific follow-up questions and sample ideal answers.
2. Behavioural Questions:
   - Role-specific STAR-method questions focusing on collaboration, leadership, conflict resolution, or project delivery.
3. Situational Questions:
   - Realistic workplace and architecture scenarios matching the job responsibilities.

Return a JSON object conforming to:
{{
  "job_title": "{job_title}",
  "candidate_name": "{cand_name}",
  "technical_questions": [
    {{
      "category": "technical",
      "difficulty": "Beginner|Intermediate|Advanced",
      "question_text": "...",
      "target_skill": "...",
      "sample_ideal_answer": "...",
      "follow_up_question": "...",
      "evaluation_criteria": "..."
    }}
  ],
  "behavioural_questions": [
    {{
      "category": "behavioural",
      "difficulty": "Intermediate",
      "question_text": "...",
      "target_skill": "...",
      "sample_ideal_answer": "...",
      "follow_up_question": "...",
      "evaluation_criteria": "..."
    }}
  ],
  "situational_questions": [
    {{
      "category": "situational",
      "difficulty": "Advanced",
      "question_text": "...",
      "target_skill": "...",
      "sample_ideal_answer": "...",
      "follow_up_question": "...",
      "evaluation_criteria": "..."
    }}
  ]
}}
"""
            if provider.lower() in ["google", "gemini"]:
                try:
                    from google import genai
                    from google.genai import types

                    client = genai.Client(api_key=api_key)
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                        ),
                    )
                    data = json.loads(res.text)
                    return InterviewQuestionSet(**data)
                except Exception:
                    import google.generativeai as genai

                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    res = model.generate_content(
                        prompt, generation_config={"response_mime_type": "application/json"}
                    )
                    data = json.loads(res.text)
                    return InterviewQuestionSet(**data)

            elif provider.lower() in ["openai", "gpt-4"]:
                from openai import OpenAI

                client = OpenAI(api_key=api_key)
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert technical hiring manager."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                data = json.loads(res.choices[0].message.content)
                return InterviewQuestionSet(**data)

        except Exception as e:
            logger.warning(f"LLM question generation failed: {e}. Falling back to deterministic engine.")

    # 2. Deterministic Offline Question Generation Engine
    tech_qs: List[GeneratedQuestion] = []
    difficulties = ["Beginner", "Intermediate", "Advanced"]

    for skill in focus_skills[:4]:
        skill_clean = skill.strip().lower()
        if skill_clean in TECH_QUESTION_BANK:
            for diff in difficulties:
                if diff in TECH_QUESTION_BANK[skill_clean]:
                    for item in TECH_QUESTION_BANK[skill_clean][diff]:
                        tech_qs.append(
                            GeneratedQuestion(
                                category="technical",
                                difficulty=diff,
                                question_text=item["question"],
                                target_skill=item["target_skill"],
                                sample_ideal_answer=item["ideal_answer"],
                                follow_up_question=item["follow_up"],
                                evaluation_criteria=item["criteria"],
                            )
                        )

    # If some skills were not in the hardcoded map, generate dynamic template questions
    for skill in focus_skills:
        skill_clean = skill.strip().lower()
        if skill_clean not in TECH_QUESTION_BANK:
            tech_qs.append(
                GeneratedQuestion(
                    category="technical",
                    difficulty="Beginner",
                    question_text=f"What core architectural patterns or best practices do you follow when building scalable systems with {skill.title()}?",
                    target_skill=skill,
                    sample_ideal_answer=f"Candidate should articulate how {skill.title()} integrates into the software lifecycle, key APIs, error handling, and performance considerations.",
                    follow_up_question=f"What common anti-patterns or bottlenecks have you encountered when using {skill.title()} in production?",
                    evaluation_criteria=f"Familiarity with {skill.title()} syntax, paradigms, and runtime behavior.",
                )
            )
            tech_qs.append(
                GeneratedQuestion(
                    category="technical",
                    difficulty="Intermediate",
                    question_text=f"How do you test, benchmark, and optimize the throughput and latency of applications using {skill.title()}?",
                    target_skill=skill,
                    sample_ideal_answer=f"Discusses unit/integration testing strategies, profiling tools, memory management, and caching layers with {skill.title()}.",
                    follow_up_question=f"Can you walk through a production issue involving {skill.title()} that you resolved?",
                    evaluation_criteria="Hands-on debugging and optimization expertise.",
                )
            )
            tech_qs.append(
                GeneratedQuestion(
                    category="technical",
                    difficulty="Advanced",
                    question_text=f"In an enterprise microservices architecture, how do you handle concurrency, failure recovery, and data consistency when using {skill.title()}?",
                    target_skill=skill,
                    sample_ideal_answer=f"Covers distributed transactions, retry mechanisms with exponential backoff, circuit breakers, and asynchronous pipelines in {skill.title()}.",
                    follow_up_question="How would you monitor and trace distributed requests across this service?",
                    evaluation_criteria="Enterprise architecture, resilience, and distributed systems mastery.",
                )
            )

    # Behavioural Questions
    beh_qs = [
        GeneratedQuestion(
            category="behavioural",
            difficulty="Intermediate",
            question_text=b["question"],
            target_skill=b["target_skill"],
            sample_ideal_answer=b["ideal_answer"],
            follow_up_question=b["follow_up"],
            evaluation_criteria=b["criteria"],
        )
        for b in BEHAVIOURAL_QUESTIONS
    ]

    # Situational Questions
    sit_qs = [
        GeneratedQuestion(
            category="situational",
            difficulty="Advanced",
            question_text=s["question"],
            target_skill=s["target_skill"],
            sample_ideal_answer=s["ideal_answer"],
            follow_up_question=s["follow_up"],
            evaluation_criteria=s["criteria"],
        )
        for s in SITUATIONAL_QUESTIONS
    ]

    return InterviewQuestionSet(
        job_title=job_title,
        candidate_name=cand_name,
        technical_questions=tech_qs[:6],
        behavioural_questions=beh_qs[:3],
        situational_questions=sit_qs[:2],
    )
