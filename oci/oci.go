package main

import (
	"C"
	"context"
	"fmt"
	"io/ioutil"
	"os"

	"github.com/cnabio/cnab-go/bundle"
	containerdRemotes "github.com/containerd/containerd/remotes"
	"github.com/docker/cnab-to-oci/remotes"
	"github.com/docker/distribution/reference"
	"github.com/docker/docker/client"
	"github.com/docker/go/canonical/json"
	"github.com/sirupsen/logrus"
)
import "github.com/docker/cli/cli/config"

//export Pull
func Pull(targetRef, outFile, outRel string) int64 {
	ref, err := reference.ParseNormalizedNamed(targetRef)
	if err != nil {
		logrus.Errorf("cannot parse normalized reference %v: %v", targetRef, err)
		return 1
	}

	b, relocationMap, err := remotes.Pull(context.Background(), ref, createResolver(nil))
	if err != nil {
		logrus.Errorf("cannot pull bundle: %v", err)
		return 1
	}

	if err := writeOutput(outFile, b); err != nil {
		logrus.Errorf("cannot write bundle: %v", err)
		return 1
	}

	if err := writeOutput(outRel, relocationMap); err != nil {
		logrus.Errorf("cannot write relocation map: %v", err)
		return 1
	}

	return 0
}

//export Push
func Push(targetRef, file string) int64 {
	var b bundle.Bundle
	bf, err := ioutil.ReadFile(file)
	if err != nil {
		logrus.Errorf("cannot read input bundle file %v: %v", file, err)
		return 1
	}
	if err := json.Unmarshal(bf, &b); err != nil {
		logrus.Errorf("cannot unmarshal bundle from file: %v", err)
		return 1
	}

	ref, err := reference.ParseNormalizedNamed(targetRef)
	if err != nil {
		logrus.Errorf("cannot parse normalized reference %v: %v", targetRef, err)
		return 1
	}

	cli, err := client.NewClientWithOpts(client.FromEnv)
	if err != nil {
		logrus.Errorf("cannot instantiate Docker client: %v", err)
		return 1
	}

	opts := []remotes.FixupOption{
		remotes.WithEventCallback(displayEvent),
		// TODO: remove
		remotes.WithAutoBundleUpdate(),
		remotes.WithPushImages(cli, os.Stdout),
	}

	res := createResolver(nil)
	rm, err := remotes.FixupBundle(context.Background(), &b, ref, res, opts...)
	if err != nil {
		logrus.Errorf("cannot fixup bundle: %v", err)
		return 1
	}

	d, err := remotes.Push(context.Background(), &b, rm, ref, res, true)
	if err != nil {
		logrus.Errorf("cannot push bundle: %v", err)
		return 1
	}
	logrus.Infof("pushed bundle with digest %v", d.Digest)

	return 0
}

func writeOutput(file string, data interface{}) error {
	bytes, err := json.MarshalCanonical(data)
	if err != nil {
		return err
	}
	if file == "-" {
		fmt.Fprintln(os.Stdout, string(bytes))
		return nil
	}
	return ioutil.WriteFile(file, bytes, 0644)
}

func createResolver(insecureRegistries []string) containerdRemotes.Resolver {
	return remotes.CreateResolver(config.LoadDefaultConfigFile(os.Stderr), insecureRegistries...)
}

func displayEvent(ev remotes.FixupEvent) {
	switch ev.EventType {
	case remotes.FixupEventTypeCopyImageStart:
		fmt.Fprintf(os.Stderr, "Starting to copy image %s...\n", ev.SourceImage)
	case remotes.FixupEventTypeCopyImageEnd:
		if ev.Error != nil {
			fmt.Fprintf(os.Stderr, "Failed to copy image %s: %s\n", ev.SourceImage, ev.Error)
		} else {
			fmt.Fprintf(os.Stderr, "Completed image %s copy\n", ev.SourceImage)
		}
	}
}

func main() {}
