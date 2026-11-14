# 文件上传下载与内容边界测试（R-18）

一句话：**上传的每一个字节都由攻击者控制**——扩展名、Content-Type、文件名、像素数、解压后体积、`Content-Disposition`，任何一处被信任，都会变成 RCE、存储型 XSS、路径穿越或存储放大。

适用：任何接收文件（头像/附件/导入/图片/压缩包/文档）或提供下载/预签名直传的项目；纯文本 API 无文件面则不适用。
配套：`assets/upload-security-matrix-template.md`（矩阵）、`scripts/upload-audit.py`（`scan` / `spec` / `cases`）。
相关规则：R-18（本手册）、R-6 隐私（EXIF/文档元数据）、R-12 身份（上传鉴权与对象级授权）、R-4 多租户（对象前缀不是授权）。**对象 key 可枚举 ≠ 有权限**，与多租户 FILE 面共用夹具。

## 0. 触发条件与不适用

| 场景 | 是否触发 | 说明 |
|---|---|---|
| 任意文件/图片/附件上传 | ✅ 必做 | 全节 |
| 只接收 JSON 文本、无文件字段 | ❌ 不适用 | 只写「不适用：无文件上传面」，**不得**写「上传安全」 |
| 预签名直传对象存储 | ✅ 必做 §3 | URL 是 bearer token，大小/类型不由签名限制 |
| 仅内部可信系统互传、无用户输入 | ◐ 部分 | 仍要验解压炸弹与处理器策略 |

## 1. 内容边界：不要相信客户端说的类型

判定顺序（三道闸，缺一不可）：

1. **扩展名白名单**（不是黑名单）：只允许业务需要的后缀；黑名单永远漏 `.phtml/.php5/.pht/.jspx/.aspx/.cgi`。
2. **Content-Type 只作参考**：客户端可任意设置，不能作为唯一判据。
3. **魔数 + 结构校验**：读文件头（`file-type` / `libmagic`），并做结构解析校验；**签名/魔数也不能单独使用**（多态文件、图片尾部追加脚本、ZIP 内嵌可执行）。

| 绕过手法 | 例子 | 防御 |
|---|---|---|
| 双扩展 | `shell.jpg.php`、`shell.php.jpg` | 取最后一段扩展名 + 白名单 |
| 空字节/编码 | `shell.php%00.jpg`、`shell.php\x00.jpg` | 拒绝 NUL 与控制字符 |
| 大小写/变体 | `shell.pHp`、`shell.PhP5` | 统一小写后比对 |
| 替代扩展 | `.phtml/.php5/.pht/.jsp/.jspx/.asp/.aspx` | 白名单而非黑名单 |
| NTFS ADS | `shell.asp:.jpg`、`shell.php::$DATA` | 拒绝 `:` 与尾随点/空格 |
| 前导点/连续点 | `.htaccess`、`...` | 拒绝前导点与 `..` |
| 图片马 | 合法 PNG 尾部追加 PHP/JS | 解码 + 重编码，剥附加段 |
| SVG | `<svg onload=...>`、外部实体 | 要么禁止，要么按 HTML 净化（ASVS 5.0 要求净化用户上传 SVG） |
| 解压炸弹 | 42.zip、billion laughs | 按**解压后**大小/条目数/深度限流 |

## 2. 文件名与路径

- **服务端生成**存储名（UUID/内容 hash + 白名单扩展名），客户端文件名只作展示字段且必须转义。
- 禁止把 `originalname` 拼进路径（`path.join(uploadDir, file.originalname)` 即路径穿越/覆盖）。
- 长度上限（如 255 字节）、字符白名单；拒绝 `..`、`/`、`\`、控制字符、前导点。
- 同目录同名覆盖是真实漏洞（8.3 短名/别名可被利用），存储名必须唯一。
- 下载时 `Content-Disposition` 按 RFC 6266 编码；`filename*` 用 RFC 5987 的 UTF-8 百分号编码，防头注入与截断。用户可控文件名不得直接进响应头。

## 3. 存储与访问

- 上传目录必须在 webroot **之外**（或独立域名/独立 bucket），且禁止该目录解释执行（Nginx `location` 不交给 PHP/Node；Apache `AllowOverride None` 防 `.htaccess` 覆盖）。
- 对象存储：bucket 默认私有，下载走短时签名或经应用鉴权代理；对象 key 不可作为授权凭证。
- **预签名 URL 是 bearer token**：到期前可被任何持有者复用；有效期要短（分钟级）；它**不限制大小/类型/Content-Length**（见 AWS 文档），限制必须在签发策略或服务端做。
- 下载响应加 `X-Content-Type-Options: nosniff`；非 HTML 内容不要 `inline` 渲染用户可控文件；`Content-Type` 由服务端按存储内容决定，不按客户端声明。
- 上传也要鉴权与 CSRF 防护；匿名上传必须有配额、限流与滥用检测。

## 4. 处理管线

- 图片：解码 → 校验像素/通道 → **重编码**（剥 EXIF/GPS 等元数据）；处理器本身处理不可信输入，须有资源限制（`sharp` 的 `limitInputPixels` 默认 268402689、`limitInputChannels` 默认 5，**不要设 `unlimited:true`**；ImageMagick 配 policy.xml，防 ImageTragick）。
- 压缩包：解压前限制条目数/总解压体积/嵌套深度，解压后逐条规范化路径并拒绝 `..`（zip slip）；解压到隔离目录。
- 文档：Office/PDF 解析器同样吃不可信输入；宏与外链要禁用。
- 病毒扫描/CDR 是纵深防御，不是替代上面三道闸；扫描异步化时要有 quarantine 状态，未扫描完成前不可下载。
- 临时文件写入系统临时目录并随机名，处理完删除；错误路径也不能把原文件留在可访问位置。

## 5. 缺陷判定表

| 现象 | 级别 | 判据 |
|---|---|---|
| 上传 `.php/.jsp/.aspx` 变体后能被服务器执行 | S1 | 请求原文 + 访问返回脚本输出 |
| 客户端文件名带 `../` 写出上传目录 | S1 | 落盘路径证据 |
| 上传目录在 webroot 内且可直链执行 | S1 | 直链 URL + 响应 |
| 仅靠 `Content-Type`/扩展名判定，伪造即通过 | S1 | 伪造请求 + 服务端接受 |
| 匿名可上传任意大小/数量 | S2 | 配额与限流缺失证据 |
| 图片马/双扩展绕过仍被当图片存储并可被浏览器执行 | S1 | 存储内容 + 响应头 |
| 预签名 URL 有效期过长或可无限复用 | S2 | 过期后仍 200 + 复用证据 |
| 下载 `inline` + 用户可控文件名 → XSS/头注入 | S2 | 响应头原文 |
| 解压炸弹导致内存/磁盘耗尽 | S1 | 资源曲线 + 无上限配置 |
| 上传文件元数据含 PII（GPS/作者）未剥离 | S3 | 下载文件的 EXIF 原文 |
| SVG 未净化即可上传并被同源渲染 | S1 | 渲染执行证据 |

## 6. 验证命令

```bash
# 1) 伪造 Content-Type 与扩展名（双扩展/大小写）
curl -sS -F 'file=@shell.php;type=image/png;filename=shell.jpg.php' https://host/upload -o r1.json -w '%{http_code}\n'
curl -sS -F 'file=@shell.php;filename=shell.PHP5' https://host/upload -w '%{http_code}\n'

# 2) 魔数伪造：PNG 头 + PHP 尾
printf '\x89PNG\r\n\x1a\n<?php echo 1; ?>' > poly.png
curl -sS -F 'file=@poly.png;type=image/png' https://host/upload -w '%{http_code}\n'

# 3) 路径穿越文件名
curl -sS -F 'file=@a.txt;filename=../../evil.txt' https://host/upload -w '%{http_code}\n'

# 4) 下载头
curl -sSI https://host/files/ID | grep -iE 'content-type|content-disposition|x-content-type-options'

# 5) 预签名：过期后复用
curl -sS -o /dev/null -w '%{http_code}\n' "$PRESIGNED_URL"   # 到期后再跑一次，应 403

# 6) 脚本审计
python scripts/upload-audit.py scan .
python scripts/upload-audit.py spec --file upload-spec.json --fail-on-gap
python scripts/upload-audit.py cases
```

`spec` 清单：`{"mode":"allowlist","allowed_extensions":["jpg","png"],"max_bytes":10485760,"storage_path":"/var/data/uploads","webroot":"/var/www","magic_check":true,"svg_allowed":false,"presigned_ttl_seconds":900,"download_disposition":"attachment"}`。

## 7. 报告证据写法（R-18 六项）

1. 三道闸的配置位置（扩展名白名单 / 魔数库 / 结构校验）与源码行；
2. 至少 4 条绕过尝试的**请求原文 + 状态码 + 响应体**（双扩展、大小写、伪造 Content-Type、路径穿越）；
3. 存储位置与执行性：直链 URL、响应头、是否可解释执行；
4. 处理管线限制：像素/通道、解压体积/条目数、处理器 policy；
5. 下载/预签名：`Content-Disposition`、`nosniff`、预签名有效期与过期后复用结果；
6. 未做项声明（如无 AV/沙箱环境）。

**不得**写：「用了 multer 就安全」「限制了 10MB 就防住炸弹」「改了扩展名就防住图片马」「对象 key 是 UUID 就不可枚举」。

## 8. 项目形态 → 证据

| 形态 | 必做 | 证据 |
|---|---|---|
| 头像/图片上传 | 重编码 + 元数据剥离 | 上传→下载 EXIF 对照 |
| 附件/文档 | 类型白名单 + 下载隔离 | 直链与 `nosniff` |
| ZIP 导入 | 解压限制 + zip slip | 炸弹与 `..` 用例 |
| 对象存储直传 | 预签名有效期/权限边界 | 过期复用 + 越权 key |
| 多租户文件 | 对象级授权 | A 的 key 用 B 的 token 取 |

## 9. 来源

- OWASP File Upload Cheat Sheet：https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
- OWASP ASVS 5.0（文件处理：拒绝超大图片、净化用户上传 SVG）：https://owasp.org/www-project-application-security-verification-standard/
- CWE-434 Unrestricted Upload of File with Dangerous Type：https://cwe.mitre.org/data/definitions/434.html
- CWE-22 Path Traversal：https://cwe.mitre.org/data/definitions/22.html
- CWE-409 Improper Handling of Highly Compressed Data（解压炸弹）：https://cwe.mitre.org/data/definitions/409.html
- AWS S3 presigned URL（bearer token、有效期、不限制大小/类型）：https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html
- RFC 6266 Content-Disposition：https://www.rfc-editor.org/rfc/rfc6266.html
- Fetch `X-Content-Type-Options`：https://fetch.spec.whatwg.org/#x-content-type-options-header
- sharp 构造器（`limitInputPixels` / `limitInputChannels` 默认值）：https://sharp.pixelplumbing.com/api-constructor/
- ImageTragick：https://imagetragick.com/
- `file-type`（魔数识别）：https://github.com/sindresorhus/file-type
