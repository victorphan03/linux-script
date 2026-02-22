Set WshShell = CreateObject("WScript.Shell")
' Goi file bat chay duoi nen, so 0 nghia la an hoan toan cua so
WshShell.Run "cmd /c C:\WifiAuto\check_wifi.bat", 0, False
Set WshShell = Nothing