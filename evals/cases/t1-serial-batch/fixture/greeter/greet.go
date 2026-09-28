// Package greeter 提供打招呼用的纯函数。
package greeter

import "strings"

// Greet 返回一句问候。name 为空白时用 "world"。
func Greet(name string) string {
	if strings.TrimSpace(name) == "" {
		name = "world"
	}
	return "Hello, " + name + "!"
}
