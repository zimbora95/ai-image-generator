from flask import Flask, render_template, request, jsonify
import csv

app = Flask(__name__)

def read_styles_from_csv(file_path):
    styles = {}
    with open(file_path, mode='r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            styles[row['Style']] = {
                'Prompt': row['Prompt'],
                'Negative Prompt': row['Negative Prompt']
            }
    return styles

@app.route('/get_styles', methods=['POST'])
def get_styles():
    category = request.json.get('category')
    if category == 'man':
        styles = read_styles_from_csv('AI_Image_Generator/static/styles/styles-man.csv')
    elif category == 'woman':
        styles = read_styles_from_csv('AI_Image_Generator/static/styles/styles-woman.csv')
    else:
        return jsonify({'error': 'Invalid category'}), 400

    return jsonify(styles)

# existing code... 