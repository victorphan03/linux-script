@echo off
:loop
:: Kiem tra xem may co dang ket noi mang Wifi-Khach khong
netsh wlan show interfaces | find "Wifi-Khach" >nul

:: Neu khong tim thay (errorlevel 1 tuc la bi vang mang)
if errorlevel 1 (
    netsh wlan connect name="Wifi-Khach"
)

:: Cho 10 giay roi kiem tra lai tiep (Ban co the doi so 10 thanh so khac)
timeout /t 10 >nul
goto loop