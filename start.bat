@echo off
title IG Trader
cd /d %~dp0
cmd /k ".\Scripts\activate.bat & py app.py"