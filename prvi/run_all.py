import subprocess
import sys

python = sys.executable
SEMENA = [42, 123, 999]
# P3: prsten, iste λ
# P4: prsten, različite λ
# P5: druga topologija (svi-svima), različite λ
# P6: prsten, drugačiji E (E=1), različite λ
# P3-P5: default E=2

konfiguracije = [
    {"naziv": "P3", "args": ["--topologija", "ring",
                             "--lambde", "2.0", "2.0", "2.0", "2.0"]},
    {"naziv": "P4", "args": ["--topologija", "ring",
                             "--lambde", "0.5", "1.0", "2.0", "4.0"]},
    {"naziv": "P5", "args": ["--topologija", "all_to_all",
                             "--lambde", "0.5", "1.0", "2.0", "4.0"]},
    {"naziv": "P6", "args": ["--topologija", "ring", "--E", "1",
                             "--lambde", "0.5", "1.0", "2.0", "4.0"]},
]

for seme in SEMENA:
    print("\nSEME:", seme)

    for k in konfiguracije:
        print("\nPokretanje:", k['naziv'])

        komanda = [python, "main_multiprocess.py"] + k["args"] + ["--seme", str(seme)]
        rezultat = subprocess.run(komanda, capture_output=False, text=True)

        if rezultat.returncode != 0:
            print("Greška pri pokretanju:", k['naziv'])

print("\nSva pokretanja završena.")