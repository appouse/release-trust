# Appouse release trust

Bu depo yalnız Appouse ürünlerinin (Orkestra, …) sürüm imajlarını **keyless** (Sigstore) imzalar. Kaynak kod içermez.

- `sign.yml` her 15 dakikada bir (ve elle) izinli Harbor projelerindeki **sürüm etiketli** (`vX.Y.Z`, `vX.Y.Z-rc.N`) imajlardan
  henüz imzalanmamış olanları imzalar. İzinli projeler ve etiket kuralı: [`trust.json`](trust.json).
- Herkese açık şeffaflık kaydına (Rekor) yalnız bu deponun kimliği ve imaj özeti (digest) düşer; ürünlerin özel kaynak depoları düşmez.
- Güvenin dayanağı: Harbor projelerine yalnız ürünlerin CI robotları imaj gönderebilir; bu depo yalnız imzalar.

## Doğrulama

```bash
cosign verify registry.appouse.services/orkestra/<imaj>@sha256:<özet> \
  --certificate-identity https://github.com/appouse/release-trust/.github/workflows/sign.yml@refs/heads/main \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

Kubernetes'te (Kubewarden `verify-image-signatures`) aynı kimlik ve issuer kullanılır.

**Biçimler:** imzalar cosign v3 (Sigstore bundle; doğrulama cosign ≥ 3 ister) ve geçiş dönemince cosign v2 eski (`.sig`) biçiminde atılır; Kubewarden henüz v3 biçimini doğrulayamıyor ([kubewarden/adm-controller#1237](https://github.com/kubewarden/adm-controller/issues/1237)).

---

This repository only signs Appouse release images (keyless, Sigstore); it contains no source code. The transparency log
records this repository's identity and the image digest, never the products' private source repositories.
