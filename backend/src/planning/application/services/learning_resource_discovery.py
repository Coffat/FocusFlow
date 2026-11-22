"""Deterministic official-documentation discovery, URL validation, and learner-material grounding."""

from __future__ import annotations

import ipaddress
import re
import time
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlsplit

from src.planning.application.knowledge.safe_url_fetcher import SafeUrlFetcher, UnsafeUrlError
from src.planning.domain.models.knowledge_concept import LearningResource
from src.planning.domain.models.knowledge_source import (
    KnowledgeIngestionStatus,
    KnowledgeSource,
    KnowledgeSourceType,
)
from src.shared_kernel.config import get_settings

OFFICIAL_DOC_ALLOWLIST_DOMAINS: frozenset[str] = frozenset(
    {
        "docs.python.org",
        "peps.python.org",
        "realpython.com",
        "fastapi.tiangolo.com",
        "docs.pydantic.dev",
        "docs.sqlalchemy.org",
        "alembic.sqlalchemy.org",
        "postgresql.org",
        "www.postgresql.org",
        "postgresqltutorial.com",
        "www.postgresqltutorial.com",
        "developer.mozilla.org",
        "owasp.org",
        "leetcode.com",
        "neetcode.io",
        "cp-algorithms.com",
        "angular.dev",
        "primeng.org",
        "tailwindcss.com",
        "typescriptlang.org",
        "www.typescriptlang.org",
        "react.dev",
        "nextjs.org",
        "vuejs.org",
        "nodejs.org",
        "go.dev",
        "pkg.go.dev",
        "kubernetes.io",
        "ebpf.io",
        "docs.kernel.org",
        "doc.rust-lang.org",
        "rust-lang.org",
        "www.rust-lang.org",
        "kafka.apache.org",
        "docs.docker.com",
        "docs.aws.amazon.com",
        "aws.amazon.com",
        "learn.microsoft.com",
        "redis.io",
        "microservices.io",
        "martinfowler.com",
        "numpy.org",
        "pandas.pydata.org",
        "scikit-learn.org",
        "pytorch.org",
        "ai.google.dev",
        "huggingface.co",
        "docs.oracle.com",
        "docs.spring.io",
        "spring.io",
        "ielts.org",
        "learnenglish.britishcouncil.org",
        "youtube.com",
        "www.youtube.com",
        "oreilly.com",
        "www.oreilly.com",
        "developer.hashicorp.com",
        "graphql.org",
        "grpc.io",
        "prometheus.io",
        "grafana.com",
        "docs.djangoproject.com",
        "docs.flutter.dev",
        "en.cppreference.com",
        "git-scm.com",
    }
)

_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "how",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "using",
        "with",
        "các",
        "cách",
        "cho",
        "chương",
        "cơ",
        "bản",
        "của",
        "dạng",
        "để",
        "đến",
        "hệ",
        "học",
        "khi",
        "kiến",
        "làm",
        "một",
        "nắm",
        "nâng",
        "cao",
        "nền",
        "tảng",
        "phần",
        "qua",
        "sau",
        "theo",
        "thực",
        "hành",
        "tổng",
        "từ",
        "và",
        "về",
        "với",
        "xây",
        "dựng",
    }
)

_URL_HEALTH_CACHE_TTL_SECONDS = 3600.0
_URL_HEALTH_CACHE: dict[str, tuple[float, bool]] = {}


def clear_url_health_cache() -> None:
    """Clear cached live HTTP HEAD verification results (for tests)."""
    _URL_HEALTH_CACHE.clear()


def _is_official_allowlisted_host(hostname: str) -> bool:
    host = hostname.strip().lower().rstrip(".")
    if not host:
        return False
    for allowed in OFFICIAL_DOC_ALLOWLIST_DOMAINS:
        if host == allowed or host.endswith(f".{allowed}"):
            return True
    return False


def _is_private_or_local_host(hostname: str) -> bool:
    host = hostname.strip().lower().rstrip(".")
    if not host or host == "localhost" or host.endswith((".local", ".internal", ".localhost")):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return not ip.is_global
    except ValueError:
        return False


def validate_official_resource_url(url: str) -> bool:
    """Validate that an external documentation URL is HTTPS, non-SSRF, and allowlisted."""
    cleaned = (url or "").strip()
    if not cleaned:
        return False
    parsed = urlsplit(cleaned)
    if parsed.scheme.lower() != "https":
        return False
    try:
        host, _ = SafeUrlFetcher._validate_shape(cleaned)
    except UnsafeUrlError:
        return False
    if _is_private_or_local_host(host):
        return False
    return _is_official_allowlisted_host(host)


async def verify_official_url_live(
    url: str,
    *,
    timeout_seconds: float = 3.0,
) -> bool:
    """Verify live HTTP reachability (with 1h cache) outside test/mock environments."""
    if not validate_official_resource_url(url):
        return False

    settings = get_settings()
    env_name = str(getattr(settings, "environment", "") or "").strip().lower()
    llm_provider = str(getattr(settings, "llm_provider", "") or "").strip().lower()
    if env_name in {"test", "testing"} or llm_provider in {"mock", "local_mock"}:
        return True

    now_mono = time.monotonic()
    cached = _URL_HEALTH_CACHE.get(url)
    if cached is not None and (now_mono - cached[0]) < _URL_HEALTH_CACHE_TTL_SECONDS:
        return cached[1]

    fetcher = SafeUrlFetcher(timeout_seconds=timeout_seconds, max_redirects=2)
    ok = await fetcher.probe_reachable(
        url,
        url_validator=validate_official_resource_url,
        user_agent="FocusFlow-ResourceCheck/1.0",
    )

    if len(_URL_HEALTH_CACHE) >= 512:
        _URL_HEALTH_CACHE.clear()
    _URL_HEALTH_CACHE[url] = (now_mono, ok)
    return ok


def tokenize_meaningful_terms(text: str) -> list[str]:
    """Extract normalized, non-stopword search tokens from query/title text."""
    lowered = (text or "").strip().lower()
    if not lowered:
        return []
    raw_tokens = re.findall(r"[a-z0-9à-ỹ\-\+#\.]+", lowered)
    deduped: list[str] = []
    seen: set[str] = set()
    for tok in raw_tokens:
        cleaned = tok.strip(".-")
        if len(cleaned) < 2 or cleaned in _STOPWORDS:
            continue
        if cleaned not in seen:
            seen.add(cleaned)
            deduped.append(cleaned)
    return deduped


def _matches_phrase_boundary(corpus: str, phrase: str) -> bool:
    p = phrase.strip().lower()
    if not p:
        return False
    escaped = re.escape(p)
    return re.search(rf"(?<![a-z0-9à-ỹ]){escaped}(?![a-z0-9à-ỹ])", corpus) is not None


_CURATED_TOPIC_ENTRIES: tuple[tuple[tuple[str, ...], LearningResource], ...] = (
    # Kubernetes & Cloud Native
    (
        ("kubernetes", "k8s", "kubectl", "pod", "deployment", "helm", "ingress", "cni", "kube"),
        LearningResource(
            title="Kubernetes Official Documentation: Concepts & Workloads",
            url="https://kubernetes.io/docs/concepts/overview/",
            type="DOCS",
            description="Tài liệu chính thức về kiến trúc cluster, Pods, Deployments, Services và Networking.",
            domain="kubernetes",
            concept_id="k8s-architecture-workloads",
        ),
    ),
    (
        ("kubernetes", "k8s", "kubectl", "helm", "eks", "container orchestration"),
        LearningResource(
            title="Kubernetes Basics Interactive Tutorials",
            url="https://kubernetes.io/docs/tutorials/kubernetes-basics/",
            type="TUTORIAL",
            description="Hướng dẫn thực hành triển khai, scale và cập nhật ứng dụng trên Kubernetes.",
            domain="kubernetes",
            concept_id="k8s-architecture-workloads",
        ),
    ),
    # eBPF & Linux Kernel Observability
    (
        ("ebpf", "bpf", "xdp", "cilium", "libbpf", "kprobe", "tracepoint", "kernel observability"),
        LearningResource(
            title="eBPF.io: What is eBPF? Architecture & Use Cases",
            url="https://ebpf.io/what-is-ebpf/",
            type="DOCS",
            description="Tài liệu chính thức về kiến trúc eBPF, verifier, maps, hooks và ứng dụng observability/networking.",
            domain="ebpf",
            concept_id="ebpf-kernel-observability",
        ),
    ),
    (
        ("ebpf", "bpf", "xdp", "libbpf", "linux kernel", "bpf_prog"),
        LearningResource(
            title="Linux Kernel BPF Documentation",
            url="https://docs.kernel.org/bpf/index.html",
            type="DOCS",
            description="Đặc tả chính thức từ Linux Kernel về BPF instruction set, verifier và helpers.",
            domain="ebpf",
            concept_id="ebpf-kernel-observability",
        ),
    ),
    # Go (Golang)
    (
        ("golang", "go", "goroutine", "goroutines", "channels", "go modules", "gin", "gRPC go"),
        LearningResource(
            title="Effective Go — Official Go Documentation",
            url="https://go.dev/doc/effective_go",
            type="DOCS",
            description="Cẩm nang chính thức viết mã Go idiomatic: goroutines, channels, interfaces và error handling.",
            domain="go",
            concept_id="go-fundamentals-concurrency",
        ),
    ),
    (
        ("golang", "go", "tour of go", "goroutine"),
        LearningResource(
            title="A Tour of Go — Official Interactive Guide",
            url="https://go.dev/tour/welcome/1",
            type="TUTORIAL",
            description="Bài học tương tác chính thức từ go.dev về cú pháp, concurrency và generics trong Go.",
            domain="go",
            concept_id="go-fundamentals-concurrency",
        ),
    ),
    # Rust
    (
        ("rust", "rustlang", "cargo", "ownership", "borrow checker", "lifetimes", "tokio"),
        LearningResource(
            title="The Rust Programming Language (Official Book)",
            url="https://doc.rust-lang.org/book/",
            type="BOOK",
            description="Giáo trình chính thức về Ownership, Borrowing, Lifetimes, Traits và Async Rust.",
            domain="rust",
            concept_id="rust-ownership-async",
        ),
    ),
    (
        ("rust", "rustlang", "std", "cargo", "tokio", "trait"),
        LearningResource(
            title="Rust Standard Library Official Reference",
            url="https://doc.rust-lang.org/std/",
            type="DOCS",
            description="Tài liệu tra cứu chính thức các module chuẩn, collections, sync và concurrency của Rust.",
            domain="rust",
            concept_id="rust-ownership-async",
        ),
    ),
    # Apache Kafka & Distributed Systems
    (
        (
            "kafka",
            "apache kafka",
            "event streaming",
            "consumer group",
            "kafka streams",
            "broker",
            "partition",
        ),
        LearningResource(
            title="Apache Kafka Official Documentation",
            url="https://kafka.apache.org/documentation/",
            type="DOCS",
            description="Tài liệu chính thức về kiến trúc Broker, Topic/Partition, Producer/Consumer và Kafka Streams.",
            domain="distributed-systems",
            concept_id="dist-kafka-event-streaming",
        ),
    ),
    (
        (
            "distributed systems",
            "distributed",
            "consensus",
            "raft",
            "paxos",
            "saga",
            "event sourcing",
            "cqrs",
            "replication",
            "two-phase commit",
        ),
        LearningResource(
            title="Patterns of Distributed Systems — Martin Fowler",
            url="https://martinfowler.com/articles/patterns-of-distributed-systems/",
            type="DOCS",
            description="Tổng hợp các mẫu thiết kế hệ thống phân tán cốt lõi: Consensus, WAL, Idempotent Receiver, Lease.",
            domain="distributed-systems",
            concept_id="dist-kafka-event-streaming",
        ),
    ),
    # Docker & Containers
    (
        ("docker", "dockerfile", "docker compose", "container", "containers", "oci"),
        LearningResource(
            title="Docker Official Get Started Guide",
            url="https://docs.docker.com/get-started/",
            type="DOCS",
            description="Hướng dẫn chính thức về containerization, Dockerfile multi-stage build, networking và volumes.",
            domain="devops",
            concept_id="docker-containers-compose",
        ),
    ),
    (
        ("docker compose", "docker", "multi-container"),
        LearningResource(
            title="Docker Compose Official Documentation",
            url="https://docs.docker.com/compose/",
            type="DOCS",
            description="Tài liệu chính thức điều phối nhiều container bằng compose.yaml.",
            domain="devops",
            concept_id="docker-containers-compose",
        ),
    ),
    # AWS & Cloud Architecture
    (
        ("aws", "amazon web services", "iam", "vpc", "ec2", "s3", "lambda", "ecs", "eks", "cloud"),
        LearningResource(
            title="AWS Official Documentation",
            url="https://docs.aws.amazon.com/",
            type="DOCS",
            description="Tài liệu chính thức cho các dịch vụ AWS cốt lõi: IAM, VPC, EC2, S3, RDS, ECS và Lambda.",
            domain="cloud",
            concept_id="cloud-aws-core-iam-vpc",
        ),
    ),
    (
        ("aws", "well-architected", "cloud architecture", "cloud"),
        LearningResource(
            title="AWS Well-Architected Framework",
            url="https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html",
            type="DOCS",
            description="Chuẩn thiết kế kiến trúc đám mây an toàn, bền vững, hiệu năng cao và tối ưu chi phí.",
            domain="cloud",
            concept_id="cloud-aws-core-iam-vpc",
        ),
    ),
    # React & Next.js
    (
        ("react", "reactjs", "jsx", "react hooks", "useeffect", "usestate", "server components"),
        LearningResource(
            title="React Official Learn Documentation",
            url="https://react.dev/learn",
            type="DOCS",
            description="Tài liệu React hiện đại chính thức về Components, Hooks, State và Rendering.",
            domain="frontend",
            concept_id="fe-react-nextjs-app-router",
        ),
    ),
    (
        ("nextjs", "next.js", "app router", "rsc", "ssr", "react"),
        LearningResource(
            title="Next.js Official App Router Documentation",
            url="https://nextjs.org/docs",
            type="DOCS",
            description="Tài liệu chính thức Next.js về App Router, Server Actions, Routing và Caching.",
            domain="frontend",
            concept_id="fe-react-nextjs-app-router",
        ),
    ),
    # Java & Spring Boot
    (
        ("java", "jvm", "jdk", "maven", "gradle", "spring", "spring boot"),
        LearningResource(
            title="Oracle Official Java Documentation",
            url="https://docs.oracle.com/en/java/",
            type="DOCS",
            description="Tài liệu ngôn ngữ Java, JVM, Collections, Concurrency và chuẩn Java SE.",
            domain="java",
            concept_id="java-spring-boot-apis",
        ),
    ),
    (
        ("spring", "spring boot", "spring security", "jpa", "hibernate", "java"),
        LearningResource(
            title="Spring Boot Official Reference Documentation",
            url="https://docs.spring.io/spring-boot/index.html",
            type="DOCS",
            description="Hướng dẫn chính thức xây dựng REST API, JPA/Hibernate và Spring Security với Spring Boot.",
            domain="java",
            concept_id="java-spring-boot-apis",
        ),
    ),
    # IELTS & Academic English
    (
        (
            "ielts",
            "academic english",
            "ielts writing",
            "ielts speaking",
            "ielts reading",
            "ielts listening",
            "ielts band",
            "english",
        ),
        LearningResource(
            title="IELTS Official Preparation Resources",
            url="https://ielts.org/take-a-test/preparation-resources",
            type="DOCS",
            description="Tài liệu luyện thi IELTS chính thức gồm đề mẫu Listening, Reading, Writing và Speaking.",
            domain="english",
            concept_id="eng-ielts-academic-skills",
        ),
    ),
    (
        ("ielts", "academic english", "british council", "english grammar", "writing"),
        LearningResource(
            title="British Council LearnEnglish Official Hub",
            url="https://learnenglish.britishcouncil.org/",
            type="PRACTICE",
            description="Kho bài học và thực hành Academic English, ngữ pháp, từ vựng và kỹ năng viết chuẩn CEFR/IELTS.",
            domain="english",
            concept_id="eng-ielts-academic-skills",
        ),
    ),
    # System Design, Architecture & Redis
    (
        (
            "system design",
            "hexagonal",
            "modular monolith",
            "ddd",
            "architecture",
            "clean architecture",
        ),
        LearningResource(
            title="Cloud & Enterprise Architecture Design Patterns — Microsoft Learn",
            url="https://learn.microsoft.com/en-us/azure/architecture/patterns/",
            type="DOCS",
            description="Danh mục mẫu kiến trúc hệ thống chuẩn công nghiệp: Circuit Breaker, CQRS, Outbox, Saga.",
            domain="system-design",
            concept_id="sys-hexagonal-modular-monolith",
        ),
    ),
    (
        ("redis", "caching", "cache", "redis streams", "pub/sub"),
        LearningResource(
            title="Redis Official Documentation",
            url="https://redis.io/docs/latest/",
            type="DOCS",
            description="Tài liệu chính thức Redis về cấu trúc dữ liệu, Caching, Streams và Persistence.",
            domain="system-design",
            concept_id="sys-caching-redis-queues",
        ),
    ),
    (
        ("outbox", "transactional outbox", "sse", "server-sent events", "event-driven"),
        LearningResource(
            title="Transactional Outbox Pattern — Microservices.io",
            url="https://microservices.io/patterns/data/transactional-outbox.html",
            type="DOCS",
            description="Đặc tả chuẩn mẫu Transactional Outbox đảm bảo nhất quán dữ liệu và sự kiện.",
            domain="system-design",
            concept_id="sys-transactional-outbox-sse",
        ),
    ),
    # Machine Learning & AI Engineering
    (
        ("pytorch", "deep learning", "neural network", "transformer", "backpropagation"),
        LearningResource(
            title="PyTorch Official Documentation",
            url="https://pytorch.org/docs/stable/index.html",
            type="DOCS",
            description="Tài liệu chính thức PyTorch về Tensors, Autograd, nn.Module và huấn luyện mô hình sâu.",
            domain="machine-learning",
            concept_id="ml-supervised-evaluation",
        ),
    ),
    (
        (
            "scikit-learn",
            "sklearn",
            "machine learning",
            "supervised learning",
            "regression",
            "classification",
        ),
        LearningResource(
            title="scikit-learn Official User Guide",
            url="https://scikit-learn.org/stable/user_guide.html",
            type="DOCS",
            description="Tài liệu chính thức về mô hình học có giám sát, Cross-Validation và đánh giá hiệu năng.",
            domain="machine-learning",
            concept_id="ml-supervised-evaluation",
        ),
    ),
    (
        ("numpy", "pandas", "data analysis", "data preprocessing", "machine learning"),
        LearningResource(
            title="NumPy & Pandas Official Documentation",
            url="https://pandas.pydata.org/docs/",
            type="DOCS",
            description="Tài liệu chính thức Pandas xử lý dữ liệu dạng bảng và vectorization.",
            domain="machine-learning",
            concept_id="ml-math-numpy-pandas",
        ),
    ),
    (
        ("llm", "gemini", "rag", "agent", "agents", "structured output", "prompt engineering"),
        LearningResource(
            title="Google Gemini API Official Documentation",
            url="https://ai.google.dev/gemini-api/docs",
            type="DOCS",
            description="Tài liệu chính thức Gemini API về Structured Outputs, Function Calling và Grounding.",
            domain="machine-learning",
            concept_id="ai-llm-structured-rag-agents",
        ),
    ),
    (
        ("huggingface", "transformers", "llm", "fine-tuning", "rag", "embeddings"),
        LearningResource(
            title="Hugging Face Official Documentation",
            url="https://huggingface.co/docs",
            type="DOCS",
            description="Tài liệu chính thức Transformers, Tokenizers, Datasets và mô hình ngôn ngữ lớn.",
            domain="machine-learning",
            concept_id="ai-llm-structured-rag-agents",
        ),
    ),
    # Additional DevOps / Backend / Mobile / Languages
    (
        ("terraform", "iac", "infrastructure as code", "hcl"),
        LearningResource(
            title="Terraform Official Documentation — HashiCorp Developer",
            url="https://developer.hashicorp.com/terraform/docs",
            type="DOCS",
            description="Tài liệu chính thức quản trị hạ tầng bằng mã nguồn với Terraform.",
            domain="devops",
            concept_id="cloud-aws-core-iam-vpc",
        ),
    ),
    (
        ("prometheus", "grafana", "observability", "metrics", "monitoring"),
        LearningResource(
            title="Prometheus Official Overview & Documentation",
            url="https://prometheus.io/docs/introduction/overview/",
            type="DOCS",
            description="Tài liệu chính thức thu thập metrics, PromQL và cảnh báo giám sát hệ thống.",
            domain="devops",
            concept_id="k8s-architecture-workloads",
        ),
    ),
    (
        ("graphql", "apollo", "schema"),
        LearningResource(
            title="GraphQL Official Learn Guide",
            url="https://graphql.org/learn/",
            type="DOCS",
            description="Tài liệu chính thức về Query, Mutation, Schema và Type System trong GraphQL.",
            domain="backend",
            concept_id="http-rest-fundamentals",
        ),
    ),
    (
        ("grpc", "protobuf", "protocol buffers"),
        LearningResource(
            title="gRPC Official Documentation",
            url="https://grpc.io/docs/",
            type="DOCS",
            description="Tài liệu chính thức thiết kế dịch vụ RPC hiệu năng cao với Protocol Buffers và HTTP/2.",
            domain="backend",
            concept_id="http-rest-fundamentals",
        ),
    ),
    (
        ("nodejs", "node.js", "express", "nestjs"),
        LearningResource(
            title="Node.js Official Learn Guide",
            url="https://nodejs.org/en/learn/getting-started/introduction-to-nodejs",
            type="DOCS",
            description="Tài liệu chính thức Node.js runtime, event loop và xử lý I/O bất đồng bộ.",
            domain="backend",
            concept_id="js-es6-async-dom",
        ),
    ),
    (
        ("django", "drf", "django rest"),
        LearningResource(
            title="Django Official Documentation",
            url="https://docs.djangoproject.com/en/stable/",
            type="DOCS",
            description="Tài liệu chính thức Django ORM, Views, Authentication và Security.",
            domain="backend",
            concept_id="fastapi-routing-pydantic",
        ),
    ),
    (
        ("vue", "vuejs", "vue.js", "nuxt"),
        LearningResource(
            title="Vue.js Official Guide",
            url="https://vuejs.org/guide/introduction.html",
            type="DOCS",
            description="Tài liệu chính thức Vue 3 Composition API, Reactivity và Components.",
            domain="frontend",
            concept_id="js-es6-async-dom",
        ),
    ),
    (
        ("flutter", "dart", "widget"),
        LearningResource(
            title="Flutter Official Documentation",
            url="https://docs.flutter.dev/",
            type="DOCS",
            description="Tài liệu chính thức xây dựng ứng dụng đa nền tảng với Flutter và Dart.",
            domain="mobile",
            concept_id="fe-react-nextjs-app-router",
        ),
    ),
    (
        ("c++", "cpp", "stl", "std::"),
        LearningResource(
            title="C++ Reference Official Documentation",
            url="https://en.cppreference.com/w/",
            type="DOCS",
            description="Tài liệu tra cứu chuẩn C++ hiện đại, STL containers, algorithms và concurrency.",
            domain="systems",
            concept_id="dsa-complexity-arrays-hashing",
        ),
    ),
    (
        ("git", "github", "version control"),
        LearningResource(
            title="Git Official Reference Manual",
            url="https://git-scm.com/doc",
            type="DOCS",
            description="Tài liệu chính thức Git branching, rebasing, merging và quy trình làm việc.",
            domain="devops",
            concept_id="docker-containers-compose",
        ),
    ),
)


def discover_curated_official_resources(
    *,
    query: str | None = None,
    concept_ids: Sequence[str] = (),
    unverified_concepts: Sequence[str] = (),
    limit: int = 6,
) -> list[LearningResource]:
    """Deterministically discover allowlisted official-doc resources for out-of-seed topics."""
    clamped_limit = max(1, min(12, int(limit)))
    search_parts = [
        str(query or "").strip(),
        *(str(c).strip() for c in concept_ids if str(c).strip()),
        *(str(u).strip() for u in unverified_concepts if str(u).strip()),
    ]
    corpus = " ".join(part for part in search_parts if part).lower()
    if not corpus:
        return []

    query_tokens = set(tokenize_meaningful_terms(corpus))
    concept_id_set = {str(c).strip().lower() for c in concept_ids if str(c).strip()}

    scored: list[tuple[float, LearningResource]] = []
    seen_urls: set[str] = set()
    for triggers, resource in _CURATED_TOPIC_ENTRIES:
        if not validate_official_resource_url(resource.url):
            continue
        if resource.url in seen_urls:
            continue

        score = 0.0
        if resource.concept_id and resource.concept_id.lower() in concept_id_set:
            score += 6.0

        for trig in triggers:
            if _matches_phrase_boundary(corpus, trig):
                score += 4.0 if " " in trig else 3.0

        if query_tokens:
            res_tokens = set(
                tokenize_meaningful_terms(
                    f"{resource.title} {resource.domain} {resource.concept_id}"
                )
            )
            overlap = len(query_tokens & res_tokens)
            if overlap > 0:
                score += float(overlap) * 1.5

        if score > 0.0:
            seen_urls.add(resource.url)
            scored.append((score, resource))

    scored.sort(key=lambda item: (-item[0], item[1].title))
    return [res for _, res in scored[:clamped_limit]]


def knowledge_source_to_learning_resource(source: KnowledgeSource) -> LearningResource | None:
    """Convert an INDEXED learner KnowledgeSource into a grounded LearningResource without leaking local paths."""
    if source.ingestion_status != KnowledgeIngestionStatus.INDEXED:
        return None

    title = (source.title or "").strip()
    if source.source_type == KnowledgeSourceType.URL:
        raw_url = str(
            (source.provenance_metadata or {}).get("final_url") or source.source_uri or ""
        ).strip()
        if not raw_url:
            return None
        parsed = urlsplit(raw_url)
        if parsed.scheme.lower() not in {"http", "https"}:
            return None
        try:
            host, _ = SafeUrlFetcher._validate_shape(raw_url)
        except UnsafeUrlError:
            return None
        if _is_private_or_local_host(host):
            return None
        safe_url = raw_url
        desc = "Nguồn học liệu URL đã được người học tải lên và lập chỉ mục."
    else:
        orig_name = str(
            (source.provenance_metadata or {}).get("original_filename")
            or title
            or "Tài liệu học tập"
        ).strip()
        safe_url = f"#knowledge-source-{source.id}"
        desc = f"Học liệu cá nhân đã lập chỉ mục ({source.source_type.value}): {orig_name}"
        if not title:
            title = orig_name

    if not title:
        title = "Học liệu cá nhân của bạn"

    return LearningResource(
        resource_id=f"src-{source.id.hex[:12]}",
        title=title[:255],
        url=safe_url,
        type="DOCS",
        description=desc,
        domain="learner-material",
        concept_id="",
    )


def match_task_fallback_resources(
    task: dict[str, Any],
    prefetched_resources: Sequence[LearningResource | dict[str, Any]],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Deterministically attach matching verified prefetched resources when task resource_ids are empty."""
    if not prefetched_resources:
        return []

    task_title = str(task.get("title") or "").strip()
    task_obj = str(task.get("learning_objective") or "").strip()
    task_desc = str(task.get("description") or "").strip()
    task_concepts = {
        str(c).strip().lower() for c in (task.get("concept_ids") or ()) if str(c).strip()
    }
    task_tokens = set(tokenize_meaningful_terms(f"{task_title} {task_obj} {task_desc}"))

    scored: list[tuple[float, dict[str, Any]]] = []
    for item in prefetched_resources:
        if isinstance(item, LearningResource):
            r_dict = item.to_dict()
        elif isinstance(item, dict):
            r_dict = dict(item)
        else:
            continue

        rid = str(r_dict.get("resource_id") or "").strip()
        r_title = str(r_dict.get("title") or "").strip()
        r_url = str(r_dict.get("url") or "").strip()
        r_desc = str(r_dict.get("description") or "").strip()
        r_domain = str(r_dict.get("domain") or "").strip().lower()
        r_cid = str(r_dict.get("concept_id") or "").strip().lower()
        if not rid or not r_title or not r_url:
            continue

        score = 0.0
        if r_cid and r_cid in task_concepts:
            score += 5.0

        res_tokens = set(tokenize_meaningful_terms(f"{r_title} {r_desc} {r_domain} {r_cid}"))
        overlap = len(task_tokens & res_tokens)
        if overlap > 0:
            score += float(overlap) * 2.0

        is_learner_material = r_domain == "learner-material" or rid.startswith("src-")
        if is_learner_material:
            # Grounded learner KnowledgeSources uploaded for this Goal always qualify if matching or as Goal material
            score += 1.5

        if score > 0.0:
            scored.append((score, r_dict))

    scored.sort(key=lambda pair: (-pair[0], str(pair[1].get("title") or "")))
    return [dict(item) for _, item in scored[: max(1, min(3, limit))]]
