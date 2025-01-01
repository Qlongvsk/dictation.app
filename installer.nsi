!include "MUI2.nsh"

Name "Dictation Practice"
OutFile "DictationPracticeSetup.exe"
InstallDir "$PROGRAMFILES\Dictation Practice"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

Section "Install"
    SetOutPath "$INSTDIR"
    
    # Copy all files from build directory
    File /r "build\exe.win-amd64-3.8\*.*"
    
    # Create start menu shortcut
    CreateDirectory "$SMPROGRAMS\Dictation Practice"
    CreateShortCut "$SMPROGRAMS\Dictation Practice\Dictation Practice.lnk" "$INSTDIR\DictationPractice.exe"
    
    # Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    # Add uninstall information to Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DictationPractice" \
                     "DisplayName" "Dictation Practice"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DictationPractice" \
                     "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
SectionEnd

Section "Uninstall"
    # Remove installed files
    RMDir /r "$INSTDIR"
    
    # Remove start menu items
    RMDir /r "$SMPROGRAMS\Dictation Practice"
    
    # Remove uninstall information
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DictationPractice"
SectionEnd 