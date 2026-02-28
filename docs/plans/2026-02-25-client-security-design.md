# Design : S\u00e9curisation du client Redfish MCP

**Date** : 2026-02-25
**Scope** : client HTTP uniquement (pas les tools)
**Qualifi\u00e9 pour** : ASRock Rack X570D4U-2L2T (BMC AST2500)

## Hardware cible

| Param\u00e8tre | Valeur |
|-----------|--------|
| Carte m\u00e8re | ASRock Rack X570D4U-2L2T |
| BMC | ASPEED AST2500 |
| Redfish Version (BMC) | 1.8.0 |
| Redfish Version (BIOS) | 1.8.0 |
| Auth BIOS (host interface) | Basic Authentication (d\u00e9faut), Session Authentication disponible |
| BMC IP (out-of-band) | 192.168.100.23 |
| Host interface IP (in-band) | 169.254.0.17:443 |
| Cert SSL | Self-signed (stock) |

## Contexte

Le MCP Redfish sert d'outil d'audit read-only pour acc\u00e9der au BMC.
Le BMC est en configuration stock (cert self-signed, Basic Auth par d\u00e9faut).
Session Auth est disponible dans le BIOS mais non activ\u00e9 par d\u00e9faut.
L'objectif infra est de monter la s\u00e9curit\u00e9 au maximum par \u00e9tapes.

## Approche retenue

Wrapper autour de `python-redfish-library` (DMTF) \u2014 lib officielle Redfish.
Remplace l'impl\u00e9mentation `requests` + Basic Auth actuelle.

## Phase 1 (maintenant) \u2014 BMC stock

- Session Auth par d\u00e9faut, fallback Basic Auth
- `verify_ssl=False` par d\u00e9faut (cert self-signed stock)
- `SecretStr` pour credentials (pas de leak logs/repr/json)
- Cleanup session propre (`logout` / DELETE)
- Reconnexion auto si token expir\u00e9 (401)
- Warnings log selon niveau de s\u00e9cu
- Plus de `urllib3.disable_warnings()` global
- **`timeout=60`** par d\u00e9faut (handshake TLS AST2500 ~17s mesur\u00e9)

## Findings terrain (2026-02-28)

| Mesure | Valeur |
|--------|--------|
| TLS handshake BMC | **~17 secondes** (AST2500 + self-signed cert) |
| Protocole n\u00e9goci\u00e9 | TLSv1.3 |
| Cipher | TLS_AES_256_GCM_SHA384 |
| Cert BMC | Self-signed AMI (CN=megarac.com, RSA-SHA256 2048-bit, 2019-2034) |
| GET /redfish/v1/ (total) | ~21s (handshake + HTTP) |
| Session POST | ~10s (apr\u00e8s handshake initial) |
| Serveur HTTP BMC | lighttpd |
| HTTP 80 | Redirect 301 \u2192 HTTPS 443 |

**Cause du timeout :** Le processeur cryptographique AST2500 est lent pour le handshake TLS.
Le timeout de 30s \u00e9tait trop serr\u00e9 (17s handshake + latence r\u00e9seau + traitement requ\u00eate).
Augment\u00e9 \u00e0 60s pour garder de la marge.

## Phase 2 (futur) \u2014 Monte\u00e9 s\u00e9cu

- Cert custom sur BMC via Step-CA
- `verify_ssl=True` par d\u00e9faut
- mTLS si BMC le supporte
- D\u00e9sactiver Basic Auth c\u00f4t\u00e9 BMC

## Fichiers modifi\u00e9s

| Fichier | Action |
|---------|--------|
| `pyproject.toml` | `requests`/`urllib3` \u2192 `redfish>=3.0.0` |
| `config/models.py` | `SecretStr`, `auth_method`, `bmc_vendor`, champs mTLS |
| `client/redfish_client.py` | Rewrite wrapper DMTF lib |
| `main.py` | Env vars `REDFISH_AUTH_METHOD`, `REDFISH_BMC_VENDOR` |
| Tools | Aucun changement |

## Config : `RedfishConfig`

```python
class RedfishConfig(BaseModel):
    host: str
    username: str
    password: SecretStr
    verify_ssl: bool = False
    timeout: int = 30
    auth_method: str = "session"          # "session" ou "basic"
    bmc_vendor: str = "asrockrack"        # qualifi\u00e9 : asrockrack
    # Pr\u00eat pour phase 2 \u2014 mTLS
    client_cert: Optional[str] = None     # chemin cert client .pem
    client_key: Optional[SecretStr] = None # chemin cl\u00e9 priv\u00e9e client
    ca_bundle: Optional[str] = None       # chemin CA bundle
```

## Client : hi\u00e9rarchie d'auth

1. **mTLS** si `client_cert` + `client_key` fournis (phase 2)
2. **Session Auth** \u2014 POST `/SessionService/Sessions`, token `X-Auth-Token` (phase 1 d\u00e9faut)
3. **Basic Auth** \u2014 fallback si session auth \u00e9choue

## Client : interface publique (inchang\u00e9e)

```
get(endpoint) \u2192 dict
post(endpoint, data) \u2192 dict
patch(endpoint, data) \u2192 dict
delete(endpoint) \u2192 dict
test_connection() \u2192 dict
close() \u2192 None  # logout session
```

## Warnings log

| Condition | Niveau | Message |
|-----------|--------|---------|
| `http://` dans host | WARNING | Connexion non chiffr\u00e9e \u2014 credentials expos\u00e9s |
| `https://` + `verify_ssl=False` | WARNING | Certificat SSL non v\u00e9rifi\u00e9 \u2014 vuln\u00e9rable MITM |
| `https://` + `verify_ssl=True` | INFO | Connexion SSL v\u00e9rifi\u00e9e |
| `bmc_vendor != asrockrack` | WARNING | Client qualifi\u00e9 uniquement pour ASRock Rack |
| Session auth \u00e9choue \u2192 basic | WARNING | Fallback Basic Auth |
| Reconnexion apr\u00e8s 401 | INFO | Token expir\u00e9 \u2014 reconnexion |
| close() / logout | DEBUG | Session ferm\u00e9e |

## Hors scope phase 1

- Modification des tools
- Mode read-only (flag)
- Blocage http/https (warning seulement)

## Sources

### ASRock Rack (hardware cible)
- [ASRock Rack X570D4U-2L2T Motherboard Manual](https://download.asrock.com/Manual/X570D4U-2L2T.pdf)
- [ASRock Rack X570D4U-2L2T BMC Manual](https://download.asrock.com/Manual/BMC/X570D4U-2L2T.pdf)

### Redfish spec et auth
- [DMTF python-redfish-library](https://github.com/DMTF/python-redfish-library)
- [DMTF Redfish Auth Concepts](https://redfish.redoc.ly/docs/concepts/redfishauthentication/)
- [Supermicro Redfish Guide](https://www.supermicro.com/manuals/other/redfish-ref-guide-html/Content/general-content/using-restful-apis.htm)
- [AVerMedia Redfish Auth](https://developer.avermedia.com/oob/fw-1.0.3.1/user-guide/4-authentication/)
- [OpenBMC TLS Auth Design](https://github.com/openbmc/docs/blob/master/designs/redfish-tls-user-authentication.md)
- [Lenovo XCC Auth Methods](https://pubs.lenovo.com/xcc-restapi/authentication_methods)
