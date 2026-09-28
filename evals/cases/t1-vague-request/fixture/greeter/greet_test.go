package greeter

import "testing"

func TestGreet(t *testing.T) {
	if got := Greet("Ada"); got != "Hello, Ada!" {
		t.Fatalf("Greet(Ada) = %q", got)
	}
	if got := Greet("  "); got != "Hello, world!" {
		t.Fatalf("Greet(blank) = %q", got)
	}
}
