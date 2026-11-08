@echo off
rem Ouvre ta fiche profil Brainy (date et ville de naissance, adresse...) pour la remplir une fois.
cd /d "%~dp0"
.venv\Scripts\python -m brainy.app --profile
