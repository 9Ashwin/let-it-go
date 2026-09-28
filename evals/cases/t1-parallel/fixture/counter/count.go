// Package counter 提供一组针对整数切片的纯函数。
package counter

// Sum 返回所有元素之和。空切片返回 0。
func Sum(xs []int) int {
	total := 0
	for _, x := range xs {
		total += x
	}
	return total
}
