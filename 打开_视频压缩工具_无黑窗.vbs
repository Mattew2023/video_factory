Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

baseDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonExe = shell.ExpandEnvironmentStrings("%USERPROFILE%") & "\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
pythonwExe = shell.ExpandEnvironmentStrings("%USERPROFILE%") & "\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe"
scriptPath = baseDir & "\video_compressor_tool.py"
logPath = baseDir & "\video_compressor_startup.log"

checkCmd = "cmd /c " & Chr(34) & Chr(34) & pythonExe & Chr(34) & " -c " & Chr(34) & "import tkinter as tk; root=tk.Tk(); root.destroy(); print('Tkinter OK')" & Chr(34) & " > " & Chr(34) & logPath & Chr(34) & " 2>&1" & Chr(34)
exitCode = shell.Run(checkCmd, 0, True)

If exitCode <> 0 Then
    MsgBox "视频压缩工具打不开，是因为当前 Python 的 Tkinter 图形界面运行库不可用。" & vbCrLf & vbCrLf & _
           "我已把详细错误写入：" & vbCrLf & logPath & vbCrLf & vbCrLf & _
           "需要安装一个完整的官方 Python，或重新打包成 exe 后再双击运行。", _
           vbExclamation, "启动失败"
    WScript.Quit exitCode
End If

runCmd = Chr(34) & pythonwExe & Chr(34) & " " & Chr(34) & scriptPath & Chr(34)
shell.Run runCmd, 0, False
