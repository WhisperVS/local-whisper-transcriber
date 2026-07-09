; Local Whisper Transcriber installer script for Inno Setup
; Build steps on Windows:
; 1. Run build_exe_windows.bat first.
; 2. Install Inno Setup: winget install JRSoftware.InnoSetup
; 3. Open this .iss file in Inno Setup and click Build,
;    or run: iscc installer_inno_setup.iss

#define MyAppName "Local Whisper Transcriber"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Wicked Hamster / Local Build"
#define MyAppExeName "LocalWhisperTranscriber.exe"

[Setup]
AppId={{A8C271D9-62A6-4A35-B90E-LOCALWHISPER}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Local Whisper Transcriber
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
OutputDir=installer-output
OutputBaseFilename=LocalWhisperTranscriberSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "dist\LocalWhisperTranscriber\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
