WScript.Sleep 5000
Set WshShell = CreateObject("WScript.Shell")
Set WshEnv = WshShell.Environment("PROCESS")
WshEnv.Remove "TCL_LIBRARY"
WshEnv.Remove "TK_LIBRARY"
WshEnv.Remove "_MEIPASS"
WshEnv.Remove "_MEIPASS2"
WshShell.Run Chr(34) & "C:\Users\tntdr\.gemini\antigravity\scratch\auto_shutdown\dist\auto_shutdown.exe" & Chr(34), 0
Set WshShell = Nothing
