@echo off
rem Ouvre le navigateur de Brainy pour te connecter une fois (Doctolib par defaut).
cd /d "%~dp0"
.venv\Scripts\python -m brainy.app --login %*
