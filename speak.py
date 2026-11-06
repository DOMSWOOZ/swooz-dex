"""Local Neural / Windows SAPI Voice Speaker for SWOOZ DEX & Auto-Flipper Bot."""

import subprocess
import sys


def speak_text(text: str) -> None:
    clean = text.replace("'", "''").replace('"', "")
    ps_script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$voices = $s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo }; "
        "$zira = $voices | Where-Object { $_.Name -match 'Zira|Eva|Aria|Natural' } | Select-Object -First 1; "
        "if ($zira) { $s.SelectVoice($zira.Name) }; "
        "$s.Rate = 1; "
        f"$s.Speak('{clean}')"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=False)


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "Swooz DEX Voice Copilot is now online and watching all nine trading legs."
    speak_text(msg)
