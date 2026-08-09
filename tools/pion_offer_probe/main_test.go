package main

import "testing"

func TestObservedBindingRequestDoesNotSelectPair(t *testing.T) {
	if selectPairFromObservedBindingRequest {
		t.Fatal("observed STUN requests must not bypass normal ICE nomination")
	}
}
