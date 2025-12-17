#!/bin/bash
echo "=============================================="
echo "  QUICK DATA COLLECTION (5 minutes)"
echo "=============================================="
echo ""
echo "Starting simulation..."
./start_random.sh

# Show which nodes are Byzantine
echo ""
echo "Byzantine nodes in this run:"
cat .env | grep -E 'crash|delay|500-error'
echo ""

echo "Collecting data in 5 minutes..."
echo "Started at: $(date '+%H:%M:%S')"
echo ""

# Wait 5 minutes with countdown
for i in {5..1}; do
    printf "\rTime remaining: %2d minutes" $i
    sleep 60
done

echo ""
echo ""
echo "Time's up! Collecting data..."
./collect_real_data.sh

DATAFILE=$(ls -t byzantine_training_data_*.csv 2>/dev/null | head -1)
if [ -f "$DATAFILE" ]; then
    SAMPLES=$(($(wc -l < "$DATAFILE") - 1))  # Subtract header
    echo ""
    echo "✅ Success! Collected $SAMPLES samples"
    echo "File: $DATAFILE"
    echo ""
    echo "Next step: Run './venv/bin/python train_validated.py'"
else
    echo "❌ No data file found. Check logs."
    exit 1
fi
