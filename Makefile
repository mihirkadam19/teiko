# Grading entry points. Run on a fresh checkout in this order:
#   make setup && make pipeline && make dashboard

PYTHON ?= python3

.PHONY: setup pipeline dashboard clean

setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

# Full pipeline, start to finish, no manual intervention.
#   load_data.py               Part 1  - build + populate cell_counts.db
#   src.analysis.freq_analysis   Part 2  - output/part2_frequency_table.csv
#   src.analysis.responder_stats Part 3  - output/part3_stats_results.csv, part3_boxplot.png, part3_responder_summary.txt
#   src.analysis.subset_analysis Part 4a - output/part4_baseline_subset.csv, part4_baseline_summary.txt
#   src.analysis.avg_bcell       Part 4b - output/part4_avg_bcell.txt
pipeline:
	$(PYTHON) load_data.py
	$(PYTHON) -m src.analysis.freq_analysis
	$(PYTHON) -m src.analysis.responder_stats
	$(PYTHON) -m src.analysis.subset_analysis
	$(PYTHON) -m src.analysis.avg_bcell

dashboard:
	$(PYTHON) -m streamlit run src/dashboard.py

clean:
	rm -f cell_counts.db
	rm -rf output
