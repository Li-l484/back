from flask import Flask, abort, send_file, jsonify, request
from flask_cors import CORS
import draw
import check

app = Flask(__name__)
CORS(app)  # 启用跨域支持

@app.route('/generate-floorplan', methods=['POST'])
def generate_floorplan():
    check.get_bim_json()
    image_data= draw.plot_room_with_furniture()
    # if image_path and os.path.exists(image_path):
        # return send_file(image_path, mimetype='image/png')
    return jsonify({
        'image_data': image_data,
    })


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)