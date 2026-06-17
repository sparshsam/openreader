; OpenReader — Inno Setup Installer (Legacy/Manual Recovery Only)
; Build: run from repo root after PyInstaller build:
;   iscc installer/setup.iss

#define MyAppName "OpenReader"
#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif
#define MyAppVersion AppVersion
#define MyAppPublisher "Sparsh Sam"
#define MyAppURL "https://github.com/sparshsam/pdfreader-by-sparsh"
#define MyAppExeName "OpenReader.exe"

[Setup]
AppId={{D3A7F9E1-4B2C-4A8F-9E6D-1C5B3A7F9E01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..
OutputBaseFilename=OpenReader-{#MyAppVersion}-Setup
SetupIconFile=..\assets\openreader.ico
Compression=lzma2/ultra64
SolidCompression=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
UninstallDisplaySize=180
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
ShowLanguageDialog=no
DisableWelcomePage=no
DisableDirPage=auto
AlwaysShowDirOnReadyPage=yes

; Close OpenReader if running before install
CloseApplications=force
AppMutex=OpenReader

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce
Name: "quicklaunchicon"; Description: "Create a &Quick Launch icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
#ifdef AppSourceDir
Source: "{#AppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#else
Source: "dist\OpenReader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: quicklaunchicon

[Registry]
; Register as a PDF handler — all keys cleaned up on uninstall
Root: HKCR; Subkey: ".pdf\OpenWithProgids"; ValueType: string; ValueName: "OpenReaderPDF"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCR; Subkey: "OpenReaderPDF"; ValueType: string; ValueName: ""; ValueData: "PDF Document"; Flags: uninsdeletekey
Root: HKCR; Subkey: "OpenReaderPDF\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCR; Subkey: "OpenReaderPDF\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCR; Subkey: "OpenReaderPDF\shell\open\command"; ValueType: expandsz; ValueName: "DelegateExecute"; Flags: deletevalue

; Register application path — cleaned up on uninstall
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueName: "Path"; ValueData: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/c taskkill /f /im ""{#MyAppExeName}"" 2>nul"; Flags: runhidden

[Code]
function InitializeSetup: Boolean;
begin
  Result := True;
end;
