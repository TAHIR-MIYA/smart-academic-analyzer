"""Build the topic profile files used by document-to-topic similarity.

    python -m datasets.build_topics

Each profile = the subject name + its concept definitions + a list of extra key terms. The output files
(datasets/topics/<subject>.txt) are plain text: edit them, or add new .txt files for new subjects.
"""
from pathlib import Path

from datasets.generate_dataset import SUBJECTS

EXTRA_TERMS = {
    "Machine Learning": "supervised learning, unsupervised learning, classification, regression, training data, test data, features, labels, neural network, bias, variance, regularization, accuracy, precision, recall, loss function, model, algorithm, prediction, clustering, dimensionality reduction, ensemble, random forest, support vector machine, hyperparameter",
    "Database Management Systems": "database, relational model, table, tuple, attribute, schema, query, SQL, relational algebra, functional dependency, ACID, concurrency control, locking, recovery, foreign key, constraint, stored procedure, trigger, view, entity, relationship, data redundancy, DBMS, index, B-tree",
    "Computer Networks": "network, protocol, OSI model, TCP/IP, packet, router, switch, bandwidth, latency, ethernet, wireless, HTTP, UDP, socket, topology, LAN, WAN, gateway, MAC address, ARP, DHCP, encryption, throughput, error detection, flow control",
    "Operating Systems": "operating system, kernel, process, thread, scheduler, CPU, memory management, page table, segmentation, deadlock, synchronization, mutex, interrupt, device driver, file allocation, disk scheduling, round robin, priority scheduling, multitasking, shell, system call, fragmentation, cache, boot",
    "Data Structures": "data structure, array, pointer, node, tree, graph, sorting, searching, complexity, recursion, algorithm, big O, traversal, insertion, deletion, balanced tree, AVL tree, priority queue, adjacency matrix, adjacency list, dynamic programming, binary search, memory, collision",
    "Software Engineering": "software, requirements, design, testing, maintenance, lifecycle, SDLC, project management, risk, scrum, sprint, user story, use case, architecture, design pattern, refactoring, debugging, integration testing, quality assurance, documentation, stakeholder, prototype, deployment, bug, release",
    "Natural Language Processing": "text, corpus, language, linguistics, parsing, syntax, semantics, sentiment analysis, machine translation, word embedding, n-gram, stop words, lemmatization, bag of words, vocabulary, named entity, classification, summarization, chatbot, speech, text mining, annotation, grammar, ambiguity, transformer",
    "Digital Electronics": "digital, binary, Boolean algebra, circuit, truth table, combinational circuit, sequential circuit, adder, subtractor, encoder, register, memory, clock, state machine, latch, NAND gate, NOR gate, XOR, signal, voltage, logic level, ROM, RAM, microcontroller",
    "Thermodynamics": "heat, temperature, pressure, work, energy, system, surroundings, cycle, efficiency, refrigerator, second law, Kelvin, Joule, specific heat, adiabatic, reversible process, steam, turbine, compressor, internal energy, equilibrium, phase change, thermal, calorific value",
    "Cloud Computing": "cloud, server, data center, virtual machine, hypervisor, IaaS, PaaS, SaaS, scalability, elasticity, availability, deployment, orchestration, Kubernetes, Docker, microservices, API, storage, bandwidth, multi-tenancy, public cloud, private cloud, hybrid cloud, pay as you go, region",
}


def build(out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for subject, (_code, concepts) in SUBJECTS.items():
        body = [f"{subject}."]
        body += [f"{c.capitalize()} is {d}." for c, d in concepts.items()]
        body.append(f"Key terms: {EXTRA_TERMS[subject]}.")
        name = subject.lower().replace(" ", "_") + ".txt"
        (out_dir / name).write_text("\n".join(body) + "\n", encoding="utf-8")
        written.append(name)
    return written


if __name__ == "__main__":
    print("Wrote:", build(Path("datasets/topics")))
