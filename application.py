from flask import *
app = Flask(__name__)

class listitem:
	def __init__(self, h, c):
		self.href=h
		self.caption=c

@app.route('/')
def index():
	items=[]
	return render_template('index.html', items=items)

if __name__ == '__main__':
	app.debug=True
	app.run(host='0.0.0.0') 
