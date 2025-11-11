[Setup]
AppId={{3E5F7F5B-8B3D-4B24-A6D4-PRAYER-MUSLIM-HOME}}
AppName=Muslim Home
AppVersion=1.0.0
DefaultDirName={autopf}\Muslim Home
DefaultGroupName=Muslim Home
OutputBaseFilename=MuslimHomeSetup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\Muslim Home\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Muslim Home"; Filename: "{app}\Muslim Home.exe"; WorkingDir: "{app}"
Name: "{commondesktop}\Muslim Home"; Filename: "{app}\Muslim Home.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"