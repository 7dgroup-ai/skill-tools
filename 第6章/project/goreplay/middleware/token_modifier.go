// project/goreplay/middleware/token_modifier.go
// GoReplay 中间件：token 关联（双 Map 算法）
// 输入：STDIN 接收 hex 编码的 payload
// 输出：STDOUT 写回 hex 编码的修改后 payload
// 协议：首字节类型 1=Request, 2=Original Response, 3=Replayed Response
// 关联逻辑：
//   1) 登录请求(Request type=1, path=/api/login) → 标记 originalTokens[reqID]=empty
//   2) 登录原始响应(Response type=2) → 解析 Body.data.token → originalTokens[reqID]=token
//   3) 登录回放响应(Replayed Response type=3) → 解析 Body.data.token → tokenAliases[originalToken]=newToken
//   4) 后续请求(Request type=1, 非登录) → 读 Header token → 查 tokenAliases[old] → SetHeader 替换为新 token

package main

import (
	"bufio"
	"bytes"
	"encoding/hex"
	"fmt"
	"os"

	"github.com/bitly/go-simplejson"
	"github.com/buger/goreplay/proto"
)

func main() {
	// reqID -> 原始 token（登录原始响应时写入）
	originalTokens := make(map[string][]byte)
	// 原始 token -> 回放 token（登录回放响应时写入，后续请求读取替换）
	tokenAliases := make(map[string][]byte)

	scanner := bufio.NewScanner(os.Stdin)
	// 增大缓冲区应对大报文
	buf := make([]byte, 0, 64*1024)
	scanner.Buffer(buf, 1024*1024)

	for scanner.Scan() {
		encoded := scanner.Bytes()
		if len(encoded) == 0 {
			continue
		}

		// hex 解码
		buf := make([]byte, len(encoded)/2)
		if _, err := hex.Decode(buf, encoded); err != nil {
			debug("hex decode error:", err)
			os.Stdout.Write(encoded) // 透传原始
			os.Stdout.Write([]byte("\n"))
			continue
		}

		process(buf, &originalTokens, &tokenAliases)
	}

	if err := scanner.Err(); err != nil {
		debug("scanner error:", err)
	}
}

func process(buf []byte, orig *map[string][]byte, alias *map[string][]byte) {
	if len(buf) == 0 {
		return
	}

	payloadType := buf[0]
	hdrEnd := bytes.IndexByte(buf, '\n')
	if hdrEnd == -1 {
		hdrEnd = len(buf)
	} else {
		hdrEnd++ // 包含 \n
	}

	header := buf[:hdrEnd-1] // 去掉 \n
	meta := bytes.Split(header, []byte(" "))
	if len(meta) < 2 {
		emit(buf)
		return
	}

	reqID := string(meta[1])
	payload := buf[hdrEnd:]

	switch payloadType {
	case '1': // Request
		// 登录请求：标记等待原始响应
		if bytes.Equal(proto.Path(payload), []byte("/api/login")) {
			(*orig)[reqID] = []byte{} // 占位
			debug("Found login request:", reqID)
		} else {
			// 非登录请求：尝试替换 token
			if tok := proto.Header(payload, []byte("token")); len(tok) > 0 {
				if newTok, ok := (*alias)[string(tok)]; ok {
					payload = proto.SetHeader(payload, []byte("token"), newTok)
					buf = append(buf[:hdrEnd], payload...)
					debug("Replaced token for req:", reqID, "old:", string(tok), "new:", string(newTok))
				}
			}
		}
		emit(buf)

	case '2': // Original Response
		// 仅处理登录接口的原始响应
		if _, ok := (*orig)[reqID]; ok {
			js, err := simplejson.NewJson([]byte(proto.Body(payload)))
			if err != nil {
				debug("parse original response json error:", err)
				emit(buf)
				return
			}
			if t := js.Get("data").Get("token"); t != nil {
				if b, err := t.Bytes(); err == nil && len(b) > 0 {
					(*orig)[reqID] = b
					debug("Cached original token:", reqID, string(b))
				}
			}
		}
		// 原始响应透传（不修改）
		emit(buf)

	case '3': // Replayed Response
		// 登录回放响应：建立 old->new 映射
		if ot, ok := (*orig)[reqID]; ok {
			delete(*orig, reqID)
			js, err := simplejson.NewJson([]byte(proto.Body(payload)))
			if err != nil {
				debug("parse replayed response json error:", err)
				emit(buf)
				return
			}
			if t := js.Get("data").Get("token"); t != nil {
				if b, err := t.Bytes(); err == nil && len(b) > 0 {
					(*alias)[string(ot)] = b
					debug("Created alias:", string(ot), "->", string(b))
				}
			}
		}
		// 回放响应透传
		emit(buf)

	default:
		emit(buf)
	}
}

func emit(buf []byte) {
	dst := make([]byte, len(buf)*2+1)
	hex.Encode(dst, buf)
	dst[len(dst)-1] = '\n'
	os.Stdout.Write(dst)
}

func debug(args ...interface{}) {
	if os.Getenv("GOR_TEST") == "" {
		fmt.Fprint(os.Stderr, "[DEBUG][TOKEN-MOD] ")
		fmt.Fprintln(os.Stderr, args...)
	}
}