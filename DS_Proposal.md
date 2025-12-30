Distributed Systems Project Proposal
Design of Trust-Weighted Load-Balance Integration for Byzantine Resilient Small Distributed Systems Prepared for:
COMP6705001 - Feri Setiawan, S.Kom., M.Eng., Ph.D. Prepared by: Raisya Jasmine Zahira 2702364761 Emanuella Ivana Karunia 2702323585 Marsya Putra 2702367220 11 November 2025 0
Table of Contents
Table of Contents...............................................................................................................................................1
1. Introduction...................................................................................................................................................2
2. Background and Related Works.........................................................................................3
2.1. Summary of Literature Review......................................................................................3
3. Methodology...................................................................................................................................................6
3.1. Components..................................................................................................................6
3.2. System Design...............................................................................................................7
3.3. Technologies..................................................................................................................9
3.4. Measure of Success....................................................................................................10
Reference.................................................................................................................................11
1
1. Introduction
The utilization of Distributed Computing Techniques and Distributed Computing Systems (“DCS”) has become a foundational concept & principle in the development of modern computing. This includes, but are not limited to; Internet of Things (“IoT”), Cloud Computing, Edge Computing, and numerous variety of applications in a wide spectrum of industries. Therefore, the availability and reliability of their services are critical, demanding fault tolerance to persevere in terms of functionality and accuracy in scenarios of component failure.
Expanding on this nuance, amongst the numerous challenges of DCS performance, a significant adversity to its integrity is the Byzantine Fault; or the Byzantine Problem (or Byzantine Generals Problem), is a well-known issue, in essence; it highlights difficulties of coordination and communication between independent parties within a distributed system. In practical scenarios; this would mean cases where nodes behave unpredictably, in which their responses are delayed, incorrect, conflicting with other components. Handling this issue would necessitate Byzantine Fault Tolerance(“BFT”) Mechanisms. However, especially in resource constrained environments, significant trade offs must be outlined before implementing any fault tolerance methodology. [8]
Conventional Algorithms of Fault Tolerance, such as practical Byzantine Fault Tolerance (“pBFT”), relies on computationally expensive mechanisms to achieve their full-consensus approach (micro-awareness and inter-node accountability). In this approach, high system stability and consistency are achieved in exchange of resource wastage in resource-constrained environments (having O(N^2, O(N^3) communication complexity)). Parallel to fault tolerance mechanisms are load-balancing. [10] Load-balancing (“LB”) is an integral architectural pattern and principle in Distributed Systems, which regulates how workloads/request traffic are distributed to resources(nodes). Conventional LB Algorithms like Round Robin(“RR”) and Least-Response Time(“LRT”) emphasize efficiency, lacking in robustness and rigidity towards the aforementioned fault scenarios.
These methodologies emphasize a design constraint: efficient resource management that acknowledges both fault tolerance and load balancing in highly constrained resource environments like Edge Computing, Fog Computing and IoT.
This DCS project proposes the design, model, and implementation of Trust-Weighted Load- Balance (“TW-LB”) to Small-Scale Byzantine-Resilient Distributed Systems, in which small-scale is defined in constraints of resources beyond the amount of worker nodes. Our model aims to elevate Byzantine-Resilience and optimize management of resources by moving Byzantine-Fault mitigation from full-consensus of each worker node to the load-balancing layer/routing layer.
2
2. Background and Related Works
2.1. Summary of Literature Review
Concept
Study
Focus of Study
Relevance to Project
Limitation/Contribution
Trust weights
A Weighted Byzantine Fault Tolerance Consensus Driven Trusted Multiple Large Language Models [1]
Assigns Trust Weights Per Node
The introduction of Trust-Weight Concept in Mitigating Byzantine Scenarios. It is applied in consensus, whilst our project would apply it in Load-balancer Layer
Limitation: Large Computational Costs and Network Costs from Blockchain
Contribution: Blockchain Consensus for LLM and the exhibiting higher results from conventional BFT.
Machine learning
Comparative Study of Machine Learning Techniques for Byzantine Fault Node
Detection in Distributed Networks [2]
Machine Learning for Fault Detection
Proposes the use of SVM for Byzantine behaviour detection in simulated networks.
Limitation:
Simulated Dataset. Has Low External Validity due to not using the real world datasets
Contribution: Demonstrate how sVM has the best performance in terms of Accuracy, F1-Score, ROC-AUC compared to Decision Trees and Random Forest 3
Byzantine isolation
Byzantine-Robust Distributed Support Vector Machine [3]
Gradient Descent used to reduce the impact of Byzantine Nodes.
Implementation of SVM to eliminate outliers and find the median of the output in an attempt to minimize the impact of Byzantine nodes to overall system output
Limitation: BFT is implemented after output
Contribution: Insight on SVM implementation to mitigate Byzantine fault
Fault injection
Failure Diagnosis for Distributed Systems using Targeted Fault Injection [4]
Application of Targeted Fault Injection to predict the position of future fault to take place.
Byzantine node behaviour could be formed by implementation of various types type of faults (crash, deadlocks, and message corruption)
Limitation: Not effective to detect performance degradation (slow processing)
Contribution: Fault injection logic
Lightweight Consensus Mechanisms for Blockchain- Based Security in Edge and IoT Networks [5]
Reviewing Performance of lightweight consensus protocols in small distributed systems
Validate PBFT not being a good choice for small resource constrained distributed systems — first proposes the intervention to start in load balancer level
Limitation: Centralization Risks
Contribution: Co- seems to have ability of consensus mechanisms (Proof of Authority, PBFT, Delegated Proof of Stake, Directed Acrylic Graph
Cluster Balance: Adaptive Load Balancing in Distributed Systems via Real-Time Clustering [6]
Propose Cluster Balancing (Adaptive Load Balancer - via K Means and DBSCAN) for dynamic workload
Proposes dynamic approach in load balancing layer. Validates ability for monitoring and decision making in real time,
Limitation:
Consumption of large Computational Overhead because of 4
distribution (Cloud Environment)
should SVM/ML Model will be implemented in real time in final deliverable.
constant clustering and evaluation.
Contribution:
Achieve Better Fault Tolerance in minimal performance degradation (under 10% loss in TPS)
Trust parameter Trust and Reliability based Load Balancing Algorithm for Cloud IaaS [7]
Trust and reliability of datacenter measured by dynamic trust score based on initialization time, machine instruction per second, and fault rate
Provides insight on trust score parameters for worker nodes
Limitation: Computation capabilities and resources are not accounted for
Contribution: Trust score parameter
Table 1.1 - Literature Review Comparison and Summary 5
3. Methodology
The basis of our project methodology is the design of a resilient distributed system, especially against Byzantine Scenarios. In general, measure of resilience could be defined as;
- Availability: DS must be able to maintain a successful and correct request-response (high TPS, low error) despite some varying levels of Byzantine worker nodes.
- Real-time Adaptability: DS must be able to adapt the routing of requests according to the continuous monitoring and assessment of trust-score of their worker nodes automatically.
3.1. Components
Traffic Control Layer
Fault Injection
Utilization of defined target nodes to exhibit Byzantine Behaviour, with ratio of
Benign:Node to Byzantine following scenario ranging from Byzantine Node % {0%, 5%,
10%, 20%, 40%} (might be subject to change since maximum Byzantine Rate is
significantly higher than our baseline paper), Utilizing HTTP proxy algorithms to
intercept and simulate the Byzantine Node Behaviours. .
Load Balancer Cluster
Proposed Module: TW-LB: makes routing decisions based on trust-score/weights assigned to each node. This approach is a hybrid of traditional load cues and dynamic inputs from the trust scoring sidecars. Will be implemented in Python.
Support Vector Machines (“SVM”) classification model would be utilized in this approach to assign a trust-weight to each node to identify and mitigate Byzantine nodes. This method is proven to be most effective compared with similar models like Decision Tree and Random Forest Classifiers in Byzantine fault detection. SVM utilization of margin maximalization and RBF Kernel is also proven to perform well in noisy and overlapping behaviours of benign and adversarial (Byzantine). [quoted from our Research Method Proposal]
Worker Node Network/Layer
Worker Nodes
Byzantine and Benign Nodes (10-15 Individual Nodes). This logic will be implemented via Docker containers that would handle incoming requests via REST API/FastAPI
- Benign Nodes: return expected responses and latency
- Byzantine Nodes: shows byzantine behaviour/indicators which includes:
- Crash: node stop responding
- Lie-Latency: artificial delays
- Omission: drop requests
- Delay: delay in response
Trust Scoring Sidecar
Assigned closely to the worker node in which node responses becomes the input in
assigning a “trust-score” (ranging from 0.0-1.0 in accordance to the behaviour of the node, 6
per node), deployed parallel to each worker node. This is to be integrated as a part of the
worker node network. Configurations for this engine would depend on the results from
the SVM.
Monitoring/Node Performance Logger (Adapter Pattern)
Utilizing Prometheus Library and Server, utilize endpoints integrated to the worker nodes to collect their performance in response time, correctness, etc. Metrics Collected would be aggregated and subject to Data Analysis to Evaluate the performance of our TW-LB Module in Routing Decision and Fault Detection.
SVM Trust Scoring Configuration
Utilized to extract features of Byzantine Node Behaviours. According to Baseline Paper[7], parameters should includes;
1. Initialization time: Time taken to allocate the
resources requested and deploy them. [7]
2. Machine instruction per second (MIPS): Number
of instruction computed per second. [7]
3. Fault rate: This the number of faults in a period of
time . [7]
3.2. System Design
Context
In our initial research plan, there was oversight in using SVM Adaptively with the system design. For now, we decided it would be overkill to run the SVM in parallel with the trust-scoring engine. Therefore, currently, we shift our focus to training the SVM as best as possible to provide the best trust scoring configurations for our system and related systems. After consultation, we have also decided to omit RR and LRT as a performance baseline, and using published studies or projects more in-line with our environment and related to ML use, as well as Byzantine Scenarios. 7
Fig 3.1 Version 1 8
Fig 3.1 Version 2 of Conceptual System Design
3.3. Technologies
- Docker, Docker Compose (Container)
- Load Balancer (Python)
- Support Vector Machine_Scikit-learn (“SVM”)
- Fault Injection Engine (Python)
- Monitoring: Prometheus Server
- Statistical Analysis
- VirtualBox / VMWare:
9
3.4. Measure of Success
Hypothesis I
With < 20% of nodes showing byzantine behaviour , TW-LB demonstrates system performance levels;
(i) higher throughput(“TPS”) and,
(ii) lower mean latency than LRT (α = 0.05)
Hypothesis II The SVM Model in TW-LB demonstrates high fault-detection capabilities and reliability in varied fault scenarios, showed by:
(i) F1 > 0.80
(ii) ROC-AUC > 0.90
(iii) MCC > 0.5
Hypothesis III. For the same stability target (equal error rate and 95p latency), TW-LB’s overheads; CPU-Memory Usage, has 10% inferiority margin compared to LRT ≤
10
Reference
[1] H. Luo et al., “A Weighted Byzantine Fault Tolerance Consensus Driven Trusted
Multiple Large Language Models Network,” IEEE Transactions on Cognitive
Communications and Networking, pp. 1-1, 2025, doi:
https://doi.org/10.1109/tccn.2025.3620286.
[2] R. Pathan and S.A.Quadri, “Comparative Study of Machine Learning Techniques for
Byzantine Fault Node Detection in Distributed Networks,” International Journal For
Multidisciplinary Research, vol. 7, no. 4, Aug. 2025, doi:
https://doi.org/10.36948/ijfmr.2025.v07i04.54117.
[3] X. Wang, W. Liu, and X. Mao, “Byzantine-robust distributed support vector machine,”
Science China Mathematics, vol. 68, no. 3, pp. 707–728, Sep. 2024, doi:
https://doi.org/10.1007/s11425-023-2217-2.
[4] C. Pham et al., “Failure Diagnosis for Distributed Systems Using Targeted Fault Injection,”
IEEE Transactions on Parallel and Distributed Systems, vol. 28, no. 2, pp. 503–516, Feb.
2017, doi: https://doi.org/10.1109/TPDS.2016.2575829.
[5] Lawal Ridwan, “Lightweight Consensus Mechanisms for Blockchain- Based Security in
Edge and IoT Networks,” Sep. 01, 2025.
https://www.researchgate.net/publication/396194399_Lightweight_Consensus_Mechani
sms_for_Blockchain-_Based_Security_in_Edge_and_IoT_Networks
[6] N. Dogra, “Cluster Balance: Adaptive Load Balancing in Distributed Systems via Real-Time
Clustering,” International Journal of Research Publication and Reviews, vol. 6, no. 4, pp.
12795–12803, Apr. 2025, Available:
https://www.researchgate.net/publication/391708506_Cluster_Balance_Adaptive_Load_
Balancing_in_Distributed_Systems_via_Real-Time_Clustering 11
[7] P. Gupta, M. K. Goyal, and P. Kumar, “Trust and reliability based load balancing algorithm
for cloud IaaS,” Feb. 2013, doi: https://doi.org/10.1109/iadcc.2013.6514196.
[8] GeeksforGeeks, “Byzantine Failure in System Design,” GeeksforGeeks, Jul. 14, 2023.
https://www.geeksforgeeks.org/system-design/byzantine-failure-in-system-design/
(accessed Nov. 25, 2025).
[9] B. Burns, Designing Distributed Systems. “O’Reilly Media, Inc.,” 2018.
[10] GeeksforGeeks, “practical Byzantine Fault Tolerance(pBFT),” GeeksforGeeks, Jan. 11, 2019.
https://www.geeksforgeeks.org/computer-networks/practical-byzantine-fault-tolerance
pbft/
[11] GeeksforGeeks, “What is Load Balancer & How Load Balancing works?,” GeeksforGeeks,
Oct. 13, 2023.
https://www.geeksforgeeks.org/system-design/what-is-load-balancer-system-design/
12