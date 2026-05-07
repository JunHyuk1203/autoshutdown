Set WshShell = CreateObject("WScript.Shell")
Set WshEnv = WshShell.Environment("PROCESS")
WshEnv.Remove "_MEIPASS2"
WshShell.Run "cmd /c test_env.bat > test_env_result.txt", 0, True
