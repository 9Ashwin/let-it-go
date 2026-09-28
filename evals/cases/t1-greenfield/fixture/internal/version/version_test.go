package version

import "testing"

func TestString(t *testing.T) {
	if String() != "0.1.0" {
		t.Fatalf("String() = %q，期望 0.1.0", String())
	}
}
