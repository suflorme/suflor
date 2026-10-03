# Suflor.me — yerel kod imzası (aktarici-kur.command bunu okur). v0.12.4: takvim yardımcısı geçici (ad-hoc) imzayla
# imzalanınca her yeniden derlemede kimliği değişiyor, macOS takvim iznini düşürüyordu (3 Ekim). Bu Mac'e özel, kendinden
# imzalı bir kod imzalama sertifikası bir kez anahtar zincirine konur; uygulama hep onunla imzalanır, izin derlemeler arasında kalır.
# Sertifika yalnız yerel imza içindir; hiçbir yere gönderilmez, güvenilir kök yapılmaz.
YEREL_IMZA_AD="Suflor Yerel Imza"
yerel_imza() {  # çıktı: imza kimliği (yoksa ve kurulamazsa "-" = eski geçici imza)
  if security find-certificate -c "$YEREL_IMZA_AD" >/dev/null 2>&1; then echo "$YEREL_IMZA_AD"; return; fi
  local T P r; T="$(mktemp -d)" || { echo "-"; return; }; P="$(openssl rand -hex 16)"
  printf '[req]\ndistinguished_name=dn\nx509_extensions=ext\nprompt=no\n[dn]\nCN=%s\n[ext]\nbasicConstraints=critical,CA:false\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=critical,codeSigning\n' "$YEREL_IMZA_AD" > "$T/c.cnf"
  openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -keyout "$T/k.pem" -out "$T/c.pem" -config "$T/c.cnf" >/dev/null 2>&1 &&
    openssl pkcs12 -export -inkey "$T/k.pem" -in "$T/c.pem" -out "$T/i.p12" -passout "pass:$P" >/dev/null 2>&1 &&
    security import "$T/i.p12" -k "$HOME/Library/Keychains/login.keychain-db" -P "$P" -T /usr/bin/codesign >/dev/null 2>&1
  r=$?; rm -rf "$T"
  if [ $r = 0 ]; then echo "$YEREL_IMZA_AD"; else echo "-"; fi
}
