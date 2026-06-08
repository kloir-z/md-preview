' md_open.vbs - Markdown opener with no console window (recommended launcher)
'
' Associate .md with this script and double-click: it launches md_open.pyw
' (auto-starts the server + opens the browser) WITHOUT any black console window.
'
' Works even where pythonw is unavailable: tries pythonw -> python -> py -3.
' WScript.Shell.Run with window style 0 launches fully hidden, so even the
' console build (python.exe) shows no window.
'
' NOTE: keep this file ASCII-only. The classic VBScript engine misreads UTF-8
' without a BOM, so non-ASCII text here causes a compile error.

Option Explicit

Dim sh, fso, scriptDir, target, argStr, i, cmd, candidates, launched

Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Call md_open.pyw sitting next to this script
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
target = scriptDir & "\md_open.pyw"

' Build the argument list from the double-clicked file path(s) (%1)
argStr = ""
For i = 0 To WScript.Arguments.Count - 1
    argStr = argStr & " " & Chr(34) & WScript.Arguments(i) & Chr(34)
Next

' Interpreters to try, in order (first one that launches wins)
candidates = Array("pythonw.exe", "python.exe", "py.exe -3")

launched = False
For i = 0 To UBound(candidates)
    cmd = candidates(i) & " " & Chr(34) & target & Chr(34) & argStr
    On Error Resume Next
    ' style 0 = hidden window, False = do not wait for exit
    sh.Run cmd, 0, False
    If Err.Number = 0 Then
        launched = True
        On Error GoTo 0
        Exit For
    End If
    Err.Clear
    On Error GoTo 0
Next

If Not launched Then
    MsgBox "Python not found. One of pythonw / python / py must be on PATH.", _
           vbExclamation, "md-preview"
End If
