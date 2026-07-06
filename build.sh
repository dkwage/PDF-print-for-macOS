
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="PDFPrinter"
BUNDLE_ID="com.example.pdfprinter"   
VERSION="0.1.0"

# 1. 의존성
pip3 install -r requirements.txt pyinstaller

# 2. .app 빌드
rm -rf build dist
pyinstaller --noconfirm --windowed \
    --name "$APP_NAME" \
    --osx-bundle-identifier "$BUNDLE_ID" \
    app.py

APP="dist/$APP_NAME.app"

# 3. 메뉴바 전용: Dock 아이콘 숨김
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$APP/Contents/Info.plist" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$APP/Contents/Info.plist"

# 4. 서명 (배포 시 필수, 로컬 테스트는 생략 가능)
if [[ -n "${SIGN_ID:-}" ]]; then
  codesign --deep --force --options runtime --sign "$SIGN_ID" "$APP"
fi

# 5. pkg 생성
PKG="dist/$APP_NAME-$VERSION.pkg"
pkgbuild \
  --component "$APP" \
  --install-location /Applications \
  --identifier "$BUNDLE_ID" \
  --version "$VERSION" \
  ${PKG_SIGN_ID:+--sign "$PKG_SIGN_ID"} \
  "$PKG"

echo "빌드 완료: $PKG"

# 6. 배포 시. Apple Developer 계정 필요
if [[ -n "${NOTARY_PROFILE:-}" ]]; then
  xcrun notarytool submit "$PKG" --keychain-profile "$NOTARY_PROFILE" --wait
  xcrun stapler staple "$PKG"
  echo "공증 완료"
fi
