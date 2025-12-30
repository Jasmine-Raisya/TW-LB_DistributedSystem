# 🚀 Run the TW-LB Byzantine Resilience Experiment

This guide provides the minimal steps to clone the repository and replicate the statistical results presented in the research paper.

## 1. Prerequisites

- **Docker & Docker Compose**: Essential for container orchestration.
- **Python 3.9+**: Required for orchestration and analysis scripts.
- **Git**: To clone the repository.

## 2. Installation

```bash
# Clone the repository
git clone https://github.com/Jasmine-Raisya/TW-LB_DistributedSystem.git
cd TW-LB_DistributedSystem

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 3. Running the Statistical Experiment

The core of this research is the **Ratio-Focused Experiment**. This script automates the deployment, traffic generation, and metric collection for 0%, 10%, and 20% Byzantine ratios.

```bash
# Execute the full 3x5 iteration experiment (Estimated: 45-50 mins)
python advanced_ratio_tester.py
```

*Note: The script will automatically start/stop Docker stacks. Ensure no other processes are using port 8080 or 9094.*

## 4. Visualizing Results

Once the experiment is complete, generate the research-grade report and statistical charts:

```bash
python report_generator.py
```

### Output Artifacts:
- `EXPERIMENT_REPORT.md`: Detailed markdown report with results.
- `statistical_ratio_performance.png`: Error bar charts (Mean ± CI95).
- `twlb_performance.png`: Overall system performance visualization.

## 5. Experiment Customization

You can modify `advanced_ratio_tester.py` to change:
- `duration`: Time per iteration (default: 180s).
- `iterations`: Number of runs per ratio (default: 5).
- `byzantine_behavior`: Switch between `500-error`, `strategic_timing`, or `advanced_mixed`.

---
**Reference Document:** See [methodology_and_results.md](methodology_and_results.md) for the theoretical framework and expected performance metrics.
