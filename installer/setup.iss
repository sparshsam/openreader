; PDFReader by Sparsh — Inno Setup Installer
; ===========================================
;
; Build from repo root after PyInstaller build:
;   iscc installer/setup.iss
;
; CI builds (release.yml):
;   iscc /Q "/DAppVersion=0.x.x" "/DAppSourceDir=dist\PDFReader by Sparsh" installer/setup.iss
;
; Defines:
;   AppVersion  — semver string (default: 0.0.0-dev)
;   AppSourceDir — path to PyInstaller onedir output (default: dist\PDFReader by Sparsh)

#define MyAppName "PDFReader by Sparsh"
#define MyAppPublisher "Sparsh"
#define MyAppURL "https://github.com/sparshsam/pdfreader-by-sparsh"
#define MyAppExeName "PDFReader by Sparsh.exe"

#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif

#ifndef AppSourceDir
  #define AppSourceDir "dist\PDFReader by Sparsh"
#endif

#define MyAppVersion AppVersion
#define SetupBaseName "PDFReader-by-Sparsh-" + AppVersion + "-Setup"

; ── Setup ─────────────────────────────────────────────────────────────

[Setup]
; Identity
AppId={{D3A7F9E1-4B2C-4A8F-9E6D-1C5B3A7F9E01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; Install paths
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output
OutputDir=..\dist\installer
OutputBaseFilename={#SetupBaseName}
SetupIconFile=..\assets\pdfreader_by_sparsh.ico

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
InternalCompressLevel=ultra64

; Uninstall
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}

; Privileges
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=commandline dialog
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763

; UI
ShowLanguageDialog=no
DisableWelcomePage=no
DisableDirPage=no

; File associations (forces Windows to refresh)
ChangesAssociations=yes

; Prevent install if app is running
CloseApplications=yes
AppMutex=PDFReaderBySparsh-{#MyAppVersion}

; ── Languages ──────────────────────────────────────────────────────────

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; ── Tasks ─────────────────────────────────────────────────────────────

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce
Name: "quicklaunchicon"; Description: "Create a &Quick Launch icon"; GroupDescription: "Additional icons:"; Flags: unchecked

; ── Files ──────────────────────────────────────────────────────────────

[Files]
Source: "{#AppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Note: ignoreversion ensures files are replaced even if a previous version exists.
;       recursesubdirs copies the entire _internal/ directory tree.

; ── Icons ──────────────────────────────────────────────────────────────

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "Open PDF documents with {#MyAppName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: quicklaunchicon

; ── Registry ───────────────────────────────────────────────────────────

; Register as a PDF handler via OpenWithProgIds
Root: HKCR; Subkey: ".pdf\OpenWithProgids"; ValueType: string; ValueName: "PDFReaderbySparsh"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCR; Subkey: "PDFReaderbySparsh"; ValueType: string; ValueName: ""; ValueData: "PDF Document"; Flags: uninsdeletekey
Root: HKCR; Subkey: "PDFReaderbySparsh\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCR; Subkey: "PDFReaderbySparsh\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCR; Subkey: "PDFReaderbySparsh\shell\open\command"; ValueType: expandsz; ValueName: "DelegateExecute"; Flags: deletevalue

; Register application path
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueName: "Path"; ValueData: "{app}"

; ── Run ────────────────────────────────────────────────────────────────

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; ── Uninstall Run ──────────────────────────────────────────────────────

[UninstallRun]
Filename: "{cmd}"; Parameters: "/c taskkill /f /im ""{#MyAppExeName}"" 2>nul"; Flags: runhidden

; ── Code (Pascal Script) ──────────────────────────────────────────────

[Code]
{**
 * Check if the app is running at install time (mutex-based).
 * Inno Setup's built-in CloseApplications may not be sufficient
 * for mutex-based single-instance apps.
 *}
function InitializeSetup: Boolean;
begin
  Result := True;
end;
