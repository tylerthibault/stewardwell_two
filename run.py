import os

from src import create_app


app = create_app()


if __name__ == "__main__":
	port = int(os.environ.get("PORT", 5123))
	debug_env = os.environ.get("FLASK_DEBUG")
	debug = debug_env.lower() in {"1", "true", "yes", "on"} if debug_env is not None else "PORT" not in os.environ
	app.run(debug=debug, host="0.0.0.0", port=port)
