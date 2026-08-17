pkgname=nexora-calc
pkgver=1.0.0
pkgrel=1
pkgdesc='Modern calculator by Nexora'
arch=('any')
license=('MIT')

depends=(
    'python'
    'python-gobject'
    'gtk4'
)

source=(
    'app.py'
    'nexora-calc.desktop'
    'nexora-calc.svg'
    'LICENSE'
)

sha256sums=('SKIP' 'SKIP' 'SKIP' 'SKIP')

package() {
    install -Dm755 "$srcdir/app.py" \
        "$pkgdir/usr/bin/nexora-calc"

    install -Dm644 "$srcdir/nexora-calc.desktop" \
        "$pkgdir/usr/share/applications/nexora-calc.desktop"

    install -Dm644 "$srcdir/nexora-calc.svg" \
        "$pkgdir/usr/share/icons/hicolor/scalable/apps/nexora-calc.svg"

    install -Dm644 "$srcdir/LICENSE" \
        "$pkgdir/usr/share/licenses/nexora-calc/LICENSE"
}
