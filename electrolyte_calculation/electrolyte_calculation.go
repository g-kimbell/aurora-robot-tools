package main

import (
	"log"
	"os"
	"os/exec"
)

func main() {
	argsWithoutProg := os.Args[1:]

	cmd := exec.Command("py", append([]string{"electrolyte_calculation.py"}, argsWithoutProg...)...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	err := cmd.Run()

	if err != nil {
		log.Fatalf("cmd.Run() failed with %s\n", err)
	}

	os.Exit(cmd.ProcessState.ExitCode())
}
