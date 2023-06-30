from musabotti import bot
import subprocess

if __name__ == "__main__":
    subprocess.Popen(["java", "-jar", "./Lavalink.jar"])
    bot.run()