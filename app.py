"""
SleepScan — Flask App
Run: python app.py
Open: http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify, send_file
import os, io, zipfile
from utils.edf_reader import read_edf, read_annotations, extract_epoch_features
from utils.clustering import match_cluster, CLUSTER_PROFILES, VAR_INSIGHTS
from utils.metrics import compute_sleep_metrics
from utils.plotter import plot_hypnogram
from utils.report import generate_pdf

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

UPLOAD_FOLDER = '/tmp/sleepscan_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        age          = float(request.form.get('age', 50))
        gender       = request.form.get('gender', 'female')
        sleep_onset  = request.form.get('sleep_onset', '23:00')
        patient_id   = request.form.get('patient_id', 'PT-001')
        technologist = request.form.get('technologist', '')
        clinic       = request.form.get('clinic', '')
        night        = request.form.get('night', 'Night 1')

        # ── Handle zip upload ─────────────────────
        zip_file = request.files.get('zip_file')
        if not zip_file:
            return jsonify({'error': 'Please upload a zip file containing both EDF files.'}), 400

        zip_path = os.path.join(UPLOAD_FOLDER, 'upload.zip')
        zip_file.save(zip_path)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(UPLOAD_FOLDER)
            names = [n for n in zf.namelist() if not n.startswith('__MACOSX')]

        # Identify recording vs annotation by filename
        edf_names = [n for n in names if n.lower().endswith('.edf')]
        ann_keys  = ['hypnogram', 'annotation', '-hyp', '_hyp', 'annot']
        ann_files = [n for n in edf_names if any(k in n.lower() for k in ann_keys)]
        rec_files = [n for n in edf_names if n not in ann_files]

        # Fallback by file size if naming is ambiguous
        if not rec_files or not ann_files:
            if len(edf_names) >= 2:
                sizes = sorted(
                    [(os.path.getsize(os.path.join(UPLOAD_FOLDER, n)), n) for n in edf_names],
                    reverse=True
                )
                rec_files = [sizes[0][1]]
                ann_files  = [sizes[1][1]]
            else:
                return jsonify({'error': f'Could not identify recording and annotation files. Found: {edf_names}'}), 400

        edf_path = os.path.join(UPLOAD_FOLDER, rec_files[0])
        ann_path = os.path.join(UPLOAD_FOLDER, ann_files[0])
        print(f"Recording:  {rec_files[0]}")
        print(f"Annotation: {ann_files[0]}")

        # ── Read signals and labels ───────────────
        signals, sfreq, channel_names = read_edf(edf_path)
        stages, epoch_times           = read_annotations(ann_path)
        features_df                   = extract_epoch_features(signals, sfreq, stages, epoch_times)
        metrics                       = compute_sleep_metrics(stages)

        # ── Clustering and VAR ────────────────────
        cluster_id, cluster_name = match_cluster(age, gender, sleep_onset)
        var_insight  = VAR_INSIGHTS[cluster_id]
        cluster_desc = CLUSTER_PROFILES[cluster_id]

        # ── Hypnogram plot only ───────────────────
        hypno_img = plot_hypnogram(stages, epoch_times)

        result = {
            'patient_id':    patient_id,
            'night':         night,
            'age':           age,
            'gender':        gender,
            'sleep_onset':   sleep_onset,
            'technologist':  technologist,
            'clinic':        clinic,
            'rec_date':      request.form.get('rec_date', ''),
            'stages':        stages,
            'epoch_times':   epoch_times,
            'metrics':       metrics,
            'cluster_id':    cluster_id,
            'cluster_name':  cluster_name,
            'cluster_desc':  cluster_desc,
            'var_insight':   var_insight,
            'hypno_img':     hypno_img,
            'channel_names': channel_names,
        }

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/report', methods=['POST'])
def report():
    try:
        data      = request.get_json()
        pdf_bytes = generate_pdf(data)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"sleep_report_{data.get('patient_id','patient')}.pdf"
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
